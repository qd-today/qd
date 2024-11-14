from pydantic import AnyUrl, BaseModel


class BaseUrl(BaseModel):
    url: AnyUrl

    @property
    def path_list(self):
        if self.url.path:
            return self.url.path.strip("/").split("/")
        return None

    def get_first_path(self):
        if self.path_list:
            return self.path_list[0]
        return None

    def get_last_path(self):
        if self.path_list:
            return self.path_list[-1]
        return None


class ApiUrl(BaseUrl):
    pass


class PluginUrl(BaseUrl):
    pass
