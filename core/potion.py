class Potion:
    def __init__(self, recept: list, proerties: list, name: str = None):
        self.__recept = recept
        self.__prorperties = proerties
        
        if name is None:
            self.__name = ''.join(proerties)
        else:
            self.__name = name


