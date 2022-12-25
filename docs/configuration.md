# handcalcs configuration

**New in v1.6.0**

Handcalcs comes with configuration options to allow the user to customize the resulting $\LaTeX$ code resulting from rendering and how numbers are displayed by default. The configuration options, with their default values, are as follow:

* `decimal_separator = "."`
* `latex_block_start = "\\["`
* `latex_block_end = "\\]"`
* `math_environment_start = "aligned"`
* `math_environment_end = "aligned"`
* `line_break = "\\\\[10pt]"`
* `use_scientific_notation =  False`
* `display_precision = 3`
* `underscore_subscripts = True`
* `greek_exclusions = []`
* `param_columns = 3`
* `preferred_string_formatter = "L"`

## Config API

To set the values for any of the above configuration options, use `handcalcs.set_option()` as shown in the example below.

```python
import handcalcs.render

handcalcs.set_option("display_precision", 4)
handcalcs.set_option("param_columns", 5) 
handcalcs.set_option("line_break", "\\\\[20pt]") 
handcalcs.set_option("greek_exclusions", ["psi"]) # etc...
```
These changes now affect all cells are rendered in the current session. If you want to permanently update the `config.json` file with these changes (so handcalcs will always load up with these options), you can then call `handcalcs.save_config()` and the changes will be saved.

The auto-complete in the `handcalcs.set_option()` function demonstrates which options are available and what types of values they take.