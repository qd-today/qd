# vim: set et sw=2 ts=2 sts=2 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-02 10:07:33

window.jinja_globals = [
    'int', 'float', 'bool', 'utf8', 'unicode', 'quote_chinese',
    'b2a_hex', 'a2b_hex', 'b2a_uu', 'a2b_uu', 'b2a_base64', 'a2b_base64',
    'b2a_qp', 'a2b_qp', 'crc_hqx', 'crc32', 'format', 'b64decode',
    'b64encode', 'to_uuid', 'md5', 'sha1', 'password_hash', 'hash',
    'aes_encrypt', 'aes_decrypt', 'timestamp', 'date_time', 'is_num',
    'add', 'sub', 'multiply', 'divide', 'Faker', 'regex_replace', 'regex_escape',
    'regex_search', 'regex_findall', 'ternary', 'random', 'shuffle',
    'mandatory', 'type_debug', 'dict', 'lipsum', 'range',
    'loop_length', 'loop_first', 'loop_last', 'loop_index', 'loop_index0',
    'loop_depth', 'loop_depth0', 'loop_revindex', 'loop_revindex0',
]
jinja_globals = window.jinja_globals

Array.prototype.some ?= (f) ->
  for x in @
    return true if f x
  return false

Array.prototype.every ?= (f) ->
  for x in @
    return false if not f x
  return true

define (require, exports, module) ->
  utils = require('/static/components/utils')
  containSpecial = RegExp(/[(\ )(\~)(\!)(\@)(\#)(\$)(\%)(\^)(\&)(\*)(\()(\))(\-)(\+)(\=)(\[)(\])(\{)(\})(\|)(\\)(\;)(\:)(\')(\")(\,)(\.)(\/)(\<)(\>)(\?)(\)]+/)

  xhr = (har) ->
    for entry in har.log.entries
      if (h for h in entry.request.headers when h.name == 'X-Requested-With' and h.value == 'XMLHttpRequest').length > 0
        entry.filter_xhr = true
    return har

  mime_type = (har) ->
    for entry in har.log.entries
      mt = entry.response?.content?.mimeType

      entry.filter_mimeType = switch
        when not mt then 'other'
        when mt.indexOf('audio') == 0 then 'media'
        when mt.indexOf('image') == 0 then 'image'
        when mt.indexOf('javascript') != -1 then 'javascript'
        when mt in ['text/html', ] then 'document'
        when mt in ['text/css', 'application/x-pointplus', ] then 'style'
        # deepcode ignore DuplicateCaseBody: order is important
        when mt.indexOf('application') == 0 then 'media'
        # deepcode ignore DuplicateCaseBody: order is important
        else 'other'
    return har

  analyze_cookies = (har) ->
    # analyze where cookie from
    cookie_jar = new utils.CookieJar()
    for entry in har.log.entries
      cookies = {}
      for cookie in cookie_jar.getCookiesSync(entry.request.url, { now: new Date(entry.startedDateTime) })
        cookies[cookie.key] = cookie.value
      for cookie in entry.request.cookies
        cookie.checked = false
        if cookie.name of cookies
          if cookie.value == cookies[cookie.name]
            cookie.from_session = true
            entry.filter_from_session = true
          else
            cookie.cookie_changed = true
            entry.filter_cookie_changed = true
            #cookie_jar.setCookieSync(utils.Cookie.fromJSON(angular.toJson({
              #key: cookie.name
              #value: cookie.value
              #path: '/'
            #})), entry.request.url)
        else
          cookie.cookie_added = true
          entry.filter_cookie_added = true
          #cookie_jar.setCookieSync(utils.Cookie.fromJSON(angular.toJson({
            #key: cookie.name
            #value: cookie.value
            #path: '/'
          #})), entry.request.url)

      # update cookie from response
      for header in (h for h in entry.response?.headers || [] when h.name.toLowerCase() == 'set-cookie') || []
        entry.filter_set_cookie = true
        try
          cookie_jar.setCookieSync(header.value, entry.request.url, { now: new Date(entry.startedDateTime) })
        catch error
          console.error(error)

    return har

  sort = (har) ->
    har.log.entries = har.log.entries?.sort((a, b) ->
      if a.pageref > b.pageref
        1
      else if a.pageref < b.pageref
        -1
      else if a.startedDateTime > b.startedDateTime
        1
      else if a.startedDateTime < b.startedDateTime
        -1
      else
        0
    )
    return har

  headers = (har) ->
    to_remove_headers = ['x-devtools-emulate-network-conditions-client-id', 'cookie', 'host', 'content-length', ]
    for entry in har.log.entries
      for header, i in entry.request.headers
        if header.name.toLowerCase() not in to_remove_headers
          header.checked = true
        else
          header.checked = false
    return har

  post_data = (har) ->
    for entry in har.log.entries
      if not entry.request.postData?.text
        continue
      if not (entry.request.postData?.mimeType?.toLowerCase().indexOf("application/x-www-form-urlencoded") == 0)
        entry.request.postData.params = undefined
        continue
      result = []
      try
        for key, value of utils.querystring_parse_with_variables(entry.request.postData.text)
          result.push({ name: key, value: value })
        entry.request.postData.params = result
      catch error
        console.error(error)
        entry.request.postData.params = undefined
        continue
    return har

  replace_variables = (har, variables) ->
    variables_vk = {}
    for k, v of variables
      if k?.length and v?.length
        variables_vk[v] = k
    #console.log variables_vk, variables

    # url
    for entry in har.log.entries
      try
        url = utils.url_parse(entry.request.url, true)
      catch error
        continue
      changed = false
      for key, value of url.query
        if value of variables_vk
          url.query[key] = "{{ #{variables_vk[value]} }}"
          changed = true
      if changed
        query = utils.querystring_unparse_with_variables(url.query)
        if query
          url.search = "?#{query}"
        else
          url.search = ""
      entry.request.url = utils.url_unparse(url)
      entry.request.queryString = utils.dict2list(url.query)

      # post data
      for entry in har.log.entries
        if not entry.request.postData?.params?
          continue
        changed = false
        for each in entry.request.postData.params
          if each.value of variables_vk
            each.value = "{{ #{variables_vk[each.value]} }}"
            changed = true
        if changed
          obj = utils.list2dict(entry.request.postData.params)
          entry.request.postData.text = utils.querystring_unparse_with_variables(obj)

    return har

  rm_content = (har) ->
    for entry in har.log.entries
      if entry.response?.content?.text?
        entry.response?.content.text = undefined
    return har

  exports = {
    analyze: (har, variables = {}) ->
      if har.log?
        replace_variables((xhr mime_type analyze_cookies headers sort post_data rm_content har), variables)
      else
        har

    recommend_default: (har) ->
      domain = null
      for entry in har.log.entries
        if not domain
          domain = utils.get_domain(entry.request.url)

        if exports.variables_in_entry(entry).length > 0
          entry.recommend = true
        else if domain != utils.get_domain(entry.request.url) || entry.response?.status in [304, 0]
          entry.recommend = false
        else if entry.response?.status // 100 == 3 || entry.response.cookies?.length > 0 || entry.request.method == 'POST'
          entry.recommend = true
        else
          entry.recommend = false
      return har

    recommend: (har) ->
      for entry in har.log.entries
        entry.recommend = if entry.checked then true else false

      checked = (e for e in har.log.entries when e.checked)
      if checked.length == 0
        return exports.recommend_default(har)

      related_cookies = []
      for entry in checked
        for cookie in entry.request.cookies
          related_cookies.push(cookie.name)

      started = false
      for entry in har.log.entries by -1
        started = entry.checked if not started
        if not started
          continue
        if not entry.response?.cookies
          continue

        start_time = new Date(entry.startedDateTime)
        set_cookie = (cookie.name for cookie in entry.response?.cookies when not cookie.expires or (new Date(cookie.expires)) > start_time)
        _related_cookies = (c for c in related_cookies when c not in set_cookie)
        if related_cookies.length > _related_cookies.length
          entry.recommend = true
          related_cookies = _related_cookies
          # add pre request cookie
          for cookie in entry.request.cookies
            related_cookies.push(cookie.name)
      return har

    variables: (string) ->
      re = /{{\s*([\w]+)[^}]*?\s*}}/g
      variables_results = []
      while m = re.exec(string)
        if jQuery.inArray(m[1], jinja_globals) < 0
          variables_results.push(m[1])
        else
          tmp = /{{\s*\w+\s*\((.*)\)[^}]*?\s*}}/
          tmp = tmp.exec(m[0])
          if tmp?.length > 1
            list_tmp = tmp[1].split(",")
            for list_tmp_v in list_tmp
              tmp1 = /(^[^\d\"\'][\w]+).*?/
              tmp_v = tmp1.exec(list_tmp_v)
              if tmp_v? and not containSpecial.test(tmp_v[1]) and jQuery.inArray(tmp_v[1], jinja_globals) < 0
                variables_results.push(tmp_v[1])
      return variables_results


    variables_in_entry: (entry) ->
      result = []
      [
        [entry.request.url, ]
        (h.name for h in entry.request.headers when h.checked)
        (h.value for h in entry.request.headers when h.checked)
        (c.name for c in entry.request.cookies when c.checked)
        (c.value for c in entry.request.cookies when c.checked)
        [entry.request.postData?.text, ]
      ].forEach((list) =>
        for string in list
          for each in exports.variables(string)
            if each? not in result
              result.push(each)
      )
      if result.length > 0
        entry.filter_variables = true
      else
        entry.filter_variables = false
      return result

    find_variables: (har) ->
      result = []
      for entry in har.log.entries
        for each in @.variables_in_entry entry
          result.push each
      return result
  }

  return exports
