class Ingridient:
    def __init__ (self, name: str, image: str = "no img": str, omnisention: int, properties: list, rareness: str):
        self.__name = name
        self.__image = image
        self.__omnisention = omnisention
        self.__properties = properties
        self.__rareness = rareness
        
    @property
    def properties(self):
        return list(self.__properties)

