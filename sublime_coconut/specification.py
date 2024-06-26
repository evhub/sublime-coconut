## INFO ########################################################################
##                                                                            ##
##                         Coconut Syntax Highlighter                         ##
##                   =====================================                    ##
##                                                                            ##
##                       Version: 2.0.00.015 (20141006)                       ##
##                            File: sublime_coconut/specification.coco        ##
##                                                                            ##
##            For more information about the project, please visit            ##
##                   <https://github.com/petervaro/python>                    ##
##                    Copyright (C) 2013 - 2014 Peter Varo                    ##
##                   <https://github.com/evhub/sublime-coconut>               ##
##                    Copyright (C) 2016 Evan Hubinger                        ##
##                                                                            ##
##  This program is free software: you can redistribute it and/or modify it   ##
##   under the terms of the GNU General Public License as published by the    ##
##       Free Software Foundation, either version 3 of the License, or        ##
##                    (at your option) any later version.                     ##
##                                                                            ##
##    This program is distributed in the hope that it will be useful, but     ##
##         WITHOUT ANY WARRANTY; without even the implied warranty of         ##
##            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.            ##
##            See the GNU General Public License for more details.            ##
##                                                                            ##
##     You should have received a copy of the GNU General Public License      ##
##     along with this program, most likely a file in the root directory,     ##
##        called 'LICENSE'. If not, see <http://www.gnu.org/licenses>.        ##
##                                                                            ##
######################################################################## INFO ##

#-- CHEATSHEET ----------------------------------------------------------------#
# HOWTO: http://sublimetext.info/docs/en/reference/syntaxdefs.html
# REGEX: http://manual.macromates.com/en/regular_expressions

# Import python modules
from copy import deepcopy

# Import user modules
from .common import syntax as original

# Syntax Definition
syntax = deepcopy(original)

# Auto-recognition
syntax['fileTypes'] = ['coc', 'coco', 'coconut', 'py_template']
syntax['keyEquivalent'] = '^~O'

# Shebang
syntax['firstLineMatch'] = r'^#!/.*\bcoconut[\d.-]*\b'

# Folding marks for the TextEditor
syntax['foldingStartMarker'] = (r'^\s*((async|match|addpattern|yield|copyclosure|case)\s+)*(def|class|(?<!\\)data)\s+([.\w>]+)\s*(\((.*)\))?\s*:'
                                r'|\{\s*$|\(\s*$|\[\s*$|^\s*"""(?=.)(?!.*""")')
syntax['foldingStopMarker'] = r'^\s*$|^\s*\}|^\s*\]|^\s*\)|^\s*"""\s*$'

# Language ID
syntax['uuid'] = '7da2bcb1-621d-43b0-a187-c42d158b22ed'

# Patterns
syntax['patterns'].update({
#-- COMMENT -------------------------------------------------------------------#
        # ALL ARE COMMON

#-- KEYWORDS ------------------------------------------------------------------#
        0x0080:
        {
            'name' : 'storage.modifier.declaration.{SCOPE}',
            'match': r'\b(global|nonlocal)\b'
        },

        0x0090:
        {
            'name' : 'keyword.control.import_and_import_from.{SCOPE}',
            'match': r'\b(import|from)\b'
        },

        0x00A0:
        {
            'name' : 'keyword.control.flow_block_delimiters.{SCOPE}',
            'match':
            (
                r'\b(elif|else|except|finally|for|if|try|while|'
                r'with|break|continue|pass|raise|return|yield|'
                r'(?<!\\|\.)(match|cases?|where|then|operator))\b'
            )
        },

        0x00C0:
        {
            'name' : 'keyword.other.{SCOPE}',
            'match': r'\b(as|assert|del|\?)\b'
        },


#-- OPERATORS -----------------------------------------------------------------#
        # ALL ARE COMMON

#-- CLASS ---------------------------------------------------------------------#
        0x0110:
        {
            'name' : 'meta.class.{SCOPE}',
            'begin': r'^\s*(class|(?<!\\)data)\s+(?=[a-zA-Z_]\w*(\s*\()?)',
            'beginCaptures':
            {
                1: {'name': 'storage.type.class.{SCOPE}'}
            },
            'patterns':
            [
                {'include': '#class_entity_name'},
                # {'include': '#class_inheritance'}
            ],
            'end'  : r'\)?([ \t\r\f\v]+\w+)?[ \t\r\f\v]*(?::|=|(?=#|\n))',
            'endCaptures':
            {
                1: {'name': 'entity.other.inherited-class.{SCOPE}'},
                # 3: {'name': 'invalid.illegal.missing_section_begin.{SCOPE}'}
            }
        },


#-- FUNCTION ------------------------------------------------------------------#
        0x0120:
        {
            'name' : 'meta.function.{SCOPE}',
            'begin': r'^\s*((?:(?:async|match|addpattern|yield|copyclosure|case)\s+)*)(def)\s+(?=[a-zA-Z_][\w.]*\s*(?:\(|:|\[))|^\s*(case)\s*(?=\()|^\s*(type)\s*(?=\()',
            'beginCaptures':
            {
                1: {'name': 'storage.modifier.coroutine.{SCOPE}'},
                2: {'name': 'storage.type.function.{SCOPE}'},
                3: {'name': 'storage.type.function.{SCOPE}'},
                4: {'name': 'storage.modifier.coroutine.{SCOPE}'},
            },
            'patterns':
            [
                # Function name
                {'include': '#function_entity_name'},
                # Arguments
                {'include': '#function_arguments'},
                # Annotation assignment (function)
                {'include': '#function_annotation'}
            ],
            # TODO: add illegal
            'end': r'\s*(:|=)',
            'endCaptures':
            {
                # 2: {'name': 'invalid.illegal.missing_section_begin.{SCOPE}'}
            }
        },


#-- LAMBDA --------------------------------------------------------------------#
        # ALL ARE COMMON

#-- DECORATOR -----------------------------------------------------------------#
        # ALL ARE COMMON

#-- CONSTANTS -----------------------------------------------------------------#
        0x0160:
        {
            'name' : 'constant.language.word_like.{SCOPE}',
            'match': r'\b(None|True|False|Ellipsis|NotImplemented|TYPE_CHECKING)\b'
        },


#-- STORAGES ------------------------------------------------------------------#
        0x0180:
        {
            'name' : 'storage.type.function.{SCOPE}',
            'match': r'\b((async|match|addpattern|yield|copyclosure|case)\s+)*(def|lambda)\b'
        },


#-- BUILTINS ------------------------------------------------------------------#
        # ALL ARE COMMON

#-- MAGIC STUFFS --------------------------------------------------------------#
        # ALL ARE COMMON

#-- ETC -----------------------------------------------------------------------#
        # ALL ARE COMMON

#-- STRUCTURES ----------------------------------------------------------------#
        # ALL ARE COMMON

#-- ACCESS --------------------------------------------------------------------#
        # ALL ARE COMMON

#-- STRING --------------------------------------------------------------------#
        # ALL ARE COMMON
    })


#-- REPOSITORY ----------------------------------------------------------------#
syntax['repository'].update({
#-- COMMENTS ------------------------------------------------------------------#
        # ALL ARE COMMON

#-- CLASS ---------------------------------------------------------------------#
        # ALL ARE COMMON

#-- FUNCTION ------------------------------------------------------------------#
        # ALL ARE COMMON

#-- BUILTINS ------------------------------------------------------------------#
        # TODO: rearrange -> what is builtin function and what is builtin type?
        'builtin_functions':
        {
            'name' : 'support.function.builtin.{SCOPE}',
            'match':
            (
                r'(?<!(?<!\.)\.)\b('
                r'__import__|abs|all|any|ascii|bin|callable|(py_)?chr|compile|delattr|'
                r'dir|divmod|eval|exec|format|getattr|globals|hasattr|hash|vars|'
                r'help|(py_)?hex|id|(py_)?input|isinstance|issubclass|iter|len|locals|'
                r'(py_)?min|next|oct|ord|pow|(py_)?print|repr|round|setattr|sorted|sum|(py_)?max|'
                r'reduce|takewhile|dropwhile|tee|makedata|consume|py_raw_input|py_xrange|'
                r'addpattern|recursive_generator|memoize|fmap|_namedtuple_of|collectby|'
                r'(py_)?breakpoint|override|ident|call|safe_call|all_equal|mapreduce'
                r')\b'
            )
        },
        'builtin_types':
        {
            'name' : 'support.type.{SCOPE}',
            'match':
            (
                r'(?<!(?<!\.)\.)\b('
                r'bool|bytearray|(py_)?bytes|classmethod|complex|dict|(py_)?range|tuple|(py_)?open|'
                r'(py_)?enumerate|float|frozenset|(py_)?int|list|memoryview|(py_)?object|'
                r'property|(py_)?reversed|set|slice|staticmethod|(py_)?str|(py_)?super|type|'
                r'(py_)?map|(py_)?zip|(process|thread|async)_map|count|starmap|zip_longest|'
                r'multi_enumerate|cartesian_product|reiterable|scan|groupsof|Expected|'
                r'flip|const|lift(_apart)?|flatten|(py_)?filter|multiset|cycle|windowsof|and_then(_await)?'
                r')\b'
            )
        },

#-- ENTITY --------------------------------------------------------------------#
        'illegal_names':
        {
            'name' : 'invalid.illegal_names.name.{SCOPE}',
            'match':
            (
                r'\b('
                r'and|as|assert|break|class|continue|def|del|elif|else|except|'
                r'finally|for|from|global|if|import|in|is|lambda|nonlocal|not|'
                r'or|pass|raise|return|try|while|with|yield|_coconut\w*'
                r')\b'
            )
        },


#-- KEYWORDS ------------------------------------------------------------------#
        # ALL ARE COMMON

#-- MAGIC STUFFS --------------------------------------------------------------#
        # TODO: rearrange -> what is magic function and what is magic variable?
        'magic_function_names':
        {
            'name' : 'support.function.magic.{SCOPE}',
            'match':
            (
                r'\b__('
                r'abs|add|and|await|bool|bytes|call|ceil|complex|contains|copy|'
                r'deepcopy|del|delattr|delete|delitem|dir|div|divmod|a?enter|eq|'
                r'a?exit|float|floor|floordiv|format|ge|get|getattr|getattribute|'
                r'getinitargs|getitem|getnewargs|getstate|gt|hash|hex|iadd|'
                r'iand|idiv|ifloordiv|ilshift|imul|index|init|instancecheck|'
                r'int|invert|ior|ipow|irshift|isub|a?iter|itruediv|ixor|le|len|'
                r'lshift|lt|metaclass|missing|mod|mul|ne|neg|new|a?next|oct|or|'
                r'pos|pow|prepare|radd|rand|rdiv|rdivmod|reduce|reduce_ex|'
                r'repr|reversed|rfloordiv|rlshift|rmod|rmul|ror|round|rpow|'
                r'rrshift|rshift|rsub|rtruediv|rxor|set|setattr|setitem|'
                r'setstate|sizeof|str|sub|subclasscheck|subclasshook|truediv|'
                r'trunc|unicode|weakref|xor|matmul|fmap|set_name|iter_getitem'
                r')__\b'
            )
        },


#-- STRING --------------------------------------------------------------------#
        # ALL ARE COMMON

#-- REGEX ---------------------------------------------------------------------#
        # ALL ARE COMMON
    })
