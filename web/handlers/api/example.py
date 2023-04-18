from . import ApiBase, Argument, api_wrap


class Echo1(ApiBase):
    api_name = "回声"
    api_description = "输出 = 输入"
    api_url = "echo1"

    @api_wrap(
        arguments=(Argument(name="text", description="输入的文字", required=True),),
        example={"text": "hello world"},
    )
    async def get(self, text: str):
        return text

    post = get


class Echo2(ApiBase):
    api_name = "回声"
    api_description = "输出 = 输入"
    api_url = "echo2"

    @api_wrap(
        arguments=(Argument(name="text", description="输入的文字", required=True),),
        example={"text": "hello world"},
    )
    async def get(self, text: str):
        return text

    @api_wrap(
        arguments=(
            Argument(name="text", description="输入的文字", required=True, from_body=True),
        ),
    )
    async def post(self, text: str):
        return text


handlers = (Echo1, Echo2)
