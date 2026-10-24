Design and develop a new renderer for handcalcs v2 called ExcelRenderer. The idea is to use handcalcs to convert Python arithmetic calculations into a live, formula-based Excel spreadsheet with thoughtful formatting.

This renderer will require more planning than a more conventional renderer. Below are my thoughts on this so far:

- Each CalcLine with an actual calculation (not a param line) will become a row in the target Excel worksheet. It will be laid out over seven columns as such:
    - | assignment symbol | = | symbolic representation | = | formula | [optional] unit | comment |
 - Each CalcLine which is either a param line or a simple value assignment will become a row laid out over six columns as such:
    - | assignment symbol | = | comment | = | value | [optional] unit |
- The symbolic representation will be similar to that of the HTML renderer using subscripts, superscripts, unicode substitutions and combinations (e.g. for hat, greek letters, and sqrt symbol)
- Each assignment symbol will become a named cell that is scoped to the worksheet (not the workbook). The target of the named cell will either be the value (in the case of a param line or simple assignment) or the formula (typical calc line).
- There are a number of Python features that are incompatible with an Excel spreadsheet. If the renderer encounters any incompatible HcNode objects during rendering, the renderer should through an ExcelRendererIncompatibleError. Examples of such Python features are below:
    - for/while loops
    - with statements
    - print() calls
    - imports
    - any function that does not map to an Excel function (or cannot map cleanly)
- One HcNode that can map to an Excel formula is an ElifBlock however not all ElifBlocks are going to be compatible with an Excel worksheet representation. The features of a compatible ElifBlock, as I see currently, are as follows:
    - The internal "purpose" of the Elif block is to perform one or more variable assignments/calculations
    - Since the Excel representation can only fit one variable assignment per row of the worksheet, if an elif tree performs multiple assignments within its branches, the elif tree will need to be duplicated/pruned to break out each separate assignment onto its own line. The logic for this should probably be within its own submodule.

Regarding formatting of the final worksheet:

- I would like to have this renderer be configurable with the following options (via nested dictionaries) at instantiation:
    - Formatting of the value cell for param lines/simple assignments:
        - bold: True/False
        - text_color: hex or rgb value
        - cell_color: hex or rgb value
    - Formatting of the formula cell for typical calculations:
        - bold: True/False
        - text_color: hex or rgb value
        - cell_color: hex or rgb value
- Calc line formatting:
    - All values will be centered in their cells except:
        - Assignment symbol will be left aligned
        - Value or formula will be right aligned
        - Optional unit will be left aligned
        - Comment will be left aligned
        - Comments will be a lighter grey color and italicized
- Headings and comment lines:
    - A heading will be in a row of merged cells that span five columns
    - Contiguous comment lines will be grouped together and be in a row of merged cells that span five columns
    - Headings will be sized according to a major second typography ratio using 10 pt as the body text size