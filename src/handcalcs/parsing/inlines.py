from dataclasses import dataclass

# All attributes with renderable content should contain deques
# even if only a single value is expected (and not a collection).


@dataclass
class FunctionCall(HandCalcsObj):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine | MarkdownHeading | CommentCommand | CommentLine | InlineComment] = field(default_factory=deque)
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)
    params: deque[str] = field(default_factory=deque)

@dataclass
class InlineComment(HandCalcsObj):
    _comment: str


@dataclass
class Comprehension(HandcalcsObj):
    assigns: deque[str | Tuple]
    iterator: deque[str | FunctionBlock | List | Tuple | Dictionary | Set]
    _is_async: bool


@dataclass
class ComprehensionChain(HandCalcsBlock):
    _type: str = ""
    assign: deque[str | FunctionBlock | List | Tuple | Dictionary | Set] = field(default_factory=deque)
    key: deque[str] = field(default_factory=deque)
    value: deque[str] = field(default_factory=deque)
    comprehensions: deque[Comprehension] = field(default_factory=deque)
