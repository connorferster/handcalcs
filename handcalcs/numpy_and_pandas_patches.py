# env/bin/python
def attempt_repr_latex(x):
	try:
		return x._repr_latex_()
	except AttributeError:
		return str(x)


def series_repr_latex(self):
	latex_result = self.to_latex(formatters = [attempt_repr_latex,], escape = False)
	print(latex_result)
	replaced = latex_result.replace('tabular', 'array').replace('toprule', 'hline').replace('midrule', 'hline').replace('bottomrule','hline')
	print(replaced)
	return replaced


def dataframe_repr_latex(self):
	latex_result = self.to_latex(formatters = [attempt_repr_latex,] * len(self.columns), escape = False)
	print(latex_result)
	replaced = latex_result.replace('tabular', 'array').replace('toprule', 'hline').replace('midrule', 'hline').replace('bottomrule','hline')
	print(replaced)
	return replaced

# def series_repr_latex(self):
# 	latex_result = self.to_latex(formatters = attempt_repr_latex,)
# 	latex_result.replace('toprule')

