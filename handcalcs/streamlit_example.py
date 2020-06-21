from math import sqrt
from handcalcs import handcalc
import streamlit as st

@handcalc
def quadratic(a,b,c):
    x_1 = (-b + sqrt(b**2 - 4*a*c)) / (2*a)
    x_2 = (-b + sqrt(b**2 - 4*a*c)) / (2*a)
    return locals()

a = st.text("Value for a:")
b = st.slider("Value for b:")
c = st.slider("Value for c:")

_, latex_code = quadratic(a,b,c):
st.latex(latex_code)