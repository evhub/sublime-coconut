## INFO ########################################################################
##                                                                            ##
##                         Coconut Syntax Highlighter                         ##
##                   =====================================                    ##
##                                                                            ##
##                       Version: 2.0.00.015 (20141006)                       ##
##                            File: build.coco                                ##
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
##        called "LICENSE". If not, see <http://www.gnu.org/licenses>.        ##
##                                                                            ##
######################################################################## INFO ##

# Import python modules
import os
import sys

# Module level constants
LANGS_PATH = os.path.join(os.path.dirname(__file__), "langs")

# I/O Details of the language
coconut_details = {
    "name" : "Coconut",
    "path" : LANGS_PATH,
    "scope": "coconut",
    "comments" : {"lines": "#"},
    "test_name": "CoconutTEST",
    "test_path": "~/AppData/Roaming/Sublime Text 3/Packages/User/CoconutTEST"
}

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Process language files
if __name__ == "__main__":

    # Import tmtools modules
    try:
        from tmtools.convert import Language
    except ImportError:
        print("[ERROR] tmtools is missing: install it from http://github.com/evhub/tmtools")
        sys.exit(1)

    #------------------------------------------------------------------------------#
    # Import user modules
    from sublime_coconut.specification import syntax as coconut_syntax

    # Setup names and locations
    lang = Language(**coconut_details)
    # Convert and save language file
    lang.from_dict(coconut_syntax)
    lang.write()
