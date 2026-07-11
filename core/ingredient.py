class Ingridient:
    def __init__(
        self,
        name: str,
        image: str = "no img",
        omnisention: int = 0,
        properties: list = [],
        rareness: str = "A",
    ):
        self.__name = name
        self.__image = image
        self.__omnisention = omnisention
        self.__properties = properties
        self.__rareness = rareness

    @property
    def properties(self):
        return list(self.__properties)

    @property
    def omnisention(self):
        return int(self.__omnisention)

    @property
    def name(self):
        return self.__name
