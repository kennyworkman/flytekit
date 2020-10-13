import collections
from enum import Enum
from typing import Union, Tuple, List, Any

from flytekit import engine as flytekit_engine
from flytekit.annotated.context_manager import FlyteContext
from flytekit.common.promise import NodeOutput as _NodeOutput
from flytekit.models import literals as _literal_models


class ConjunctionOps(Enum):
    AND = "and"
    OR = "or"


class ComparisonOps(Enum):
    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="


class ComparisonExpression(object):
    def __init__(self, lhs: Union['Promise', Any], op: ComparisonOps, rhs: Union['Promise', Any]):
        _type = None
        self._op = op
        self._lhs = None
        self._rhs = None
        if isinstance(lhs, Promise):
            if lhs.is_ready:
                raise ValueError("Comparison of completed promise is not allowed.")
            self._lhs = lhs.ref
            _type = self._lhs.sdk_type
        if isinstance(rhs, Promise):
            if rhs.is_ready:
                raise ValueError("Comparison of completed promise is not allowed.")
            self._rhs = rhs.ref
            if _type is not None and _type != self._rhs.sdk_type:
                raise ValueError(f"Comparison between non comparable types {self._lhs.var} & {self._rhs.var}")
            else:
                _type = self._rhs.sdk_type
        if _type is None:
            raise ValueError("Either LHS or RHS should be a promise")
        if self._lhs is None:
            self._lhs = flytekit_engine.python_value_to_idl_literal(FlyteContext.current_context(), lhs, _type)
        if self._rhs is None:
            self._rhs = flytekit_engine.python_value_to_idl_literal(FlyteContext.current_context(), rhs, _type)

    @property
    def rhs(self) -> Union[_NodeOutput, _literal_models.Literal]:
        return self._rhs

    @property
    def lhs(self) -> Union[_NodeOutput, _literal_models.Literal]:
        return self._lhs

    @property
    def op(self) -> ComparisonOps:
        return self._op

    def __and__(self, other):
        print("Comparison AND called")
        return ConjunctionExpression(lhs=self, op=ConjunctionOps.AND, rhs=other)

    def __or__(self, other):
        print("Comparison OR called")
        return ConjunctionExpression(lhs=self, op=ConjunctionOps.OR, rhs=other)

    def __bool__(self):
        raise ValueError(
            "Cannot perform truth value testing,"
            " This is a limitation in python. For Logical `and\\or` use `&\\|` (bitwise) instead")

    def __repr__(self):
        s = "Comp( "
        if isinstance(self._lhs, _NodeOutput):
            s += f"({self._lhs.node_id},{self._lhs.var})"
        else:
            s += f"{self._lhs.short_string()}"
        s += f" {self._op.value} "
        if isinstance(self._rhs, _NodeOutput):
            s += f"({self._rhs.node_id},{self._rhs.var})"
        else:
            s += f"{self._rhs.short_string()}"
        s += " )"
        return s


class ConjunctionExpression(object):

    def __init__(self, lhs: ComparisonExpression, op: ConjunctionOps, rhs: ComparisonExpression):
        self._lhs = lhs
        self._rhs = rhs
        self._op = op

    @property
    def rhs(self) -> ComparisonExpression:
        return self._rhs

    @property
    def lhs(self) -> ComparisonExpression:
        return self._lhs

    @property
    def op(self) -> ConjunctionOps:
        return self._op

    def __and__(self, other: ComparisonExpression):
        print("Conj AND called")
        return ConjunctionExpression(lhs=self, op=ConjunctionOps.AND, rhs=other)

    def __or__(self, other):
        print("Conj OR called")
        return ConjunctionExpression(lhs=self, op=ConjunctionOps.OR, rhs=other)

    def __bool__(self):
        raise ValueError(
            "Cannot perform truth value testing,"
            " This is a limitation in python. For Logical `and\\or` use `&\\|` (bitwise) instead")

    def __repr__(self):
        return f"( {self._lhs} {self._op} {self._rhs} )"


class Promise(object):
    def __init__(self, var: str, val: Union[_NodeOutput, _literal_models.Literal]):
        self._var = var
        self._promise_ready = True
        self._val = val
        if isinstance(val, _NodeOutput):
            self._ref = val
            self._promise_ready = False
            self._val = None

    @property
    def is_ready(self) -> bool:
        """
        Returns if the Promise is READY (is not a reference and the val is actually ready)
        Usage:
           p = Promise(...)
           ...
           if p.is_ready():
                print(p.val)
           else:
                print(p.ref)
        """
        return self._promise_ready

    @property
    def val(self) -> _literal_models.Literal:
        """
        If the promise is ready then this holds the actual evaluate value in Flyte's type system
        """
        return self._val

    @property
    def ref(self) -> _NodeOutput:
        """
        If the promise is NOT READY / Incomplete, then it maps to the origin node that owns the promise
        """
        return self._ref

    @property
    def var(self) -> str:
        """
        Name of the variable bound with this promise
        """
        return self._var

    def __eq__(self, other) -> ComparisonExpression:
        return ComparisonExpression(self, ComparisonOps.EQ, other)

    def __ne__(self, other) -> ComparisonExpression:
        return ComparisonExpression(self, ComparisonOps.NE, other)

    def __gt__(self, other) -> ComparisonExpression:
        return ComparisonExpression(self, ComparisonOps.GT, other)

    def __ge__(self, other) -> ComparisonExpression:
        return ComparisonExpression(self, ComparisonOps.GE, other)

    def __lt__(self, other) -> ComparisonExpression:
        return ComparisonExpression(self, ComparisonOps.LT, other)

    def __le__(self, other) -> ComparisonExpression:
        return ComparisonExpression(self, ComparisonOps.LE, other)

    def __bool__(self):
        raise ValueError(
            "Cannot perform truth value testing,"
            " This is a limitation in python. For Logical `and\\or` use `&\\|` (bitwise) instead")

    def __and__(self, other):
        raise ValueError("Cannot perform Logical AND of Promise with other")

    def __or__(self, other):
        raise ValueError("Cannot perform Logical OR of Promise with other")

    def with_overrides(self, *args, **kwargs):
        if not self.is_ready:
            # TODO, this should be forwarded, but right now this results in failure and we want to test this behavior
            # self.ref.sdk_node.with_overrides(*args, **kwargs)
            print(f"Forwarding to node {self.ref.sdk_node.id}")
        return self

    def __repr__(self):
        if self._promise_ready:
            return f"Var({self._var}={self._val})"
        return f"Promise({self._var},{self.ref.node_id})"

    def __str__(self):
        return str(self.__repr__())


# To create a class that is a named tuple, we might have to create namedtuplemeta and manipulate the tuple
def create_task_output(promises: Union[List[Promise], Promise, None]) -> Union[Tuple[Promise], Promise, None]:
    if promises is None:
        return None

    if isinstance(promises, Promise):
        return promises

    if len(promises) == 0:
        return None

    if len(promises) == 1:
        return promises[0]

    # More than one promises, let us wrap it into a tuple
    variables = [p.var for p in promises]

    class Output(collections.namedtuple("TaskOutput", variables)):
        def with_overrides(self, *args, **kwargs):
            val = self.__getattribute__(self._fields[0])
            val.with_overrides(*args, **kwargs)
            return self

    return Output(*promises)
