# monkey patching

from forbiddenfruit import curse
curse(list, 'map', lambda self,f:list(map(f,self)))
curse(list, 'filter', lambda self,f:list(filter(f,self)))
# curse(list, 'sort', lambda self,f:sorted(self, key=f))
curse(list, 'join', lambda self,s:s.join(list(self)))
