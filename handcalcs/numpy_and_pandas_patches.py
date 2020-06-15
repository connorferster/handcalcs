# env/bin/python
try:
	from array2latex import to_latex
except:
	from . import array2latex as a2l

def attempt_repr_latex(x):
	try:
		return x._repr_latex_()
	except AttributeError:
		return str(x)


def series_repr_latex(self):
	latex_result = self.to_latex(formatters = [attempt_repr_latex,], escape = False)
	replaced = latex_result.replace('tabular', 'array').replace('toprule', 'hline').replace('midrule', 'hline').replace('bottomrule','hline')
	return replaced


def dataframe_repr_latex(self):
	latex_result = self.to_latex(formatters = [attempt_repr_latex,] * len(self.columns), escape = False)
	#print(latex_result)
	replaced = latex_result.replace('tabular', 'array').replace('toprule', 'hline').replace('midrule', 'hline').replace('bottomrule','hline')
	#print(replaced)
	return replaced

def numpy_repr_latex(array):
	return a2l.to_latex(array)

# def series_repr_latex(self):
# 	latex_result = self.to_latex(formatters = attempt_repr_latex,)
# 	latex_result.replace('toprule')

