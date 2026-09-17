"""Import shim for ANTLR-generated code.

The ANTLR Python target emits `from .SqlBaseParserBase import SqlBaseParserBase` for a grammar's
`superClass` option, so the class has to be importable from inside this
generated package. The implementation lives in dbsqlparse.antlr_base, next to
the rest of the hand-written code, rather than in this generated directory.
"""

from dbsqlparse.antlr_base import SqlBaseParserBase

__all__ = ["SqlBaseParserBase"]
