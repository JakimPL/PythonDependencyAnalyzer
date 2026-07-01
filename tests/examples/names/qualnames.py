"""Stage 1 corpus: how Python forms __qualname__ for definitions.

Each definition is annotated with the __qualname__ that Python 3.13 assigns to
it, verified against the live interpreter. The module is omitted from each
annotation; the runtime FQN is f"{__module__}.{__qualname__}". Tokens such as
<locals> and <lambda> mark a qualname as non-importable.

This file is ground-truth (Axis A: the lexical qualified name Python itself
computes). It is parsed as source by PDA, never imported by PDA.
"""

import functools


def top():  # qualname: top
    pass


class Top:  # qualname: Top
    def method(self):  # qualname: Top.method
        pass

    class Inner:  # qualname: Top.Inner
        def deep(self):  # qualname: Top.Inner.deep
            pass


def outer():  # qualname: outer
    def inner():  # qualname: outer.<locals>.inner
        pass

    return inner


module_lambda = lambda: 0  # qualname: <lambda> (the assignment target name is NOT used)


def mixed():  # qualname: mixed
    class B:  # qualname: mixed.<locals>.B
        def c(self):  # qualname: mixed.<locals>.B.c
            def d():  # qualname: mixed.<locals>.B.c.<locals>.d
                pass

            return d

    return B


def deco(fn):  # qualname: deco
    def wrapper(*args):  # qualname: deco.<locals>.wrapper
        return fn(*args)

    return wrapper


@deco
def decorated():  # def-site qualname: decorated; runtime object qualname: deco.<locals>.wrapper
    pass


def deco_wraps(fn):  # qualname: deco_wraps
    @functools.wraps(fn)
    def wrapper(*args):  # def-site: deco_wraps.<locals>.wrapper; runtime after wraps: copies wrapped fn
        return fn(*args)

    return wrapper


@deco_wraps
def decorated_wrapped():  # def-site qualname: decorated_wrapped; runtime: decorated_wrapped (wraps restores it)
    pass


class Descriptors:  # qualname: Descriptors
    @staticmethod
    def s():  # qualname: Descriptors.s
        pass

    @classmethod
    def k(cls):  # qualname: Descriptors.k
        pass

    @property
    def p(self):  # fget qualname: Descriptors.p; the property object itself has no __qualname__
        return 1


def multiplicity(cond):  # qualname: multiplicity
    if cond:

        def f():  # qualname: multiplicity.<locals>.f  (node 1)
            return 1

    else:

        def f():  # qualname: multiplicity.<locals>.f  (node 2, SAME qualname, distinct AST node)
            return 2

    return f
