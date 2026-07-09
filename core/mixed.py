from ingredients import Ingridient
from database.test_bd import PROPERTIES

class Mixed:
    def __init__ (self, ingredients: list):
        self.__ingredients = ingredients
        
        raw_properties = []
        for ing in ingredients:
            raw_properties += ing.properties

        self.__properties = self._resoulve_conflict(raw_properties)

         
   def _resoulve_conflict(self, raw_properties):
       for effect, antieffect in PROPERTIES.items():
           while (effect in raw_properties) and (antieffect in raw_properties):
                raw_properties.remove(effect)
                raw_properties.remove(antieffect)
        return raw_properties 
           

