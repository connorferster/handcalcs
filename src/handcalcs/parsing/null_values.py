from dataclasses import dataclass

@dataclass(frozen=True)
class NoValue:
    type: str = 'no_value'

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return True
        return False
    
    def __neq__(self, other):
        return False
    
    def render(self):
        return ""


@dataclass
class HcNotImplemented:
    node_name: str
    type: str = 'not_implemented'