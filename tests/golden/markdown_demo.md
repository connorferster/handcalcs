# HandCalcs v2.0 Demo

This is a demo of the main rendering features of HandCalcs v2.x. It is intended to showcase the output of a given renderer and make comparisons between renderers. This paragraph demonstrates the rendering of a series of comment lines which can be used for explanation within your Python script.

## The quadratic formula

`from math import atan, sqrt, sin, radians, degrees`

`import math`

&nbsp;

The variables 'a' and 'b' below have been formatted with different line-scopes formatting codes. Both originally have nine decimal places.

&nbsp;

$$\begin{aligned} a &= 5.25 \\ b &= -1.04231 \times 10^{1} \\ c &= 2 \\ x_{1} &= \frac{-b + \sqrt{b^{2} - 4 \cdot a \cdot c}}{2 \cdot a} = \frac{-\left(-10.423\right) + \sqrt{\left(-10.423\right)^{2} - 4 \cdot 5.2539 \cdot 2}}{2 \cdot 5.2539} = 1.7686 \\ x_{2} &= \frac{-b - \sqrt{b^{2} - 4 \cdot a \cdot c}}{2 \cdot a} = \frac{-\left(-10.423\right) - \sqrt{\left(-10.423\right)^{2} - 4 \cdot 5.2539 \cdot 2}}{2 \cdot 5.2539} = 0.21523 \end{aligned}$$

Params grid type 1

$$\begin{aligned} f &= 1 \; &g &= 2 \; &h &= 4 \; \end{aligned}$$

Params grid type 2 (Comments allowed)

$$\begin{aligned} x &= 3 \; \text{(comment 1)} \qquad &y &= 4 \qquad &z &= 5 \; \text{(last comment)} \end{aligned}$$

## Lateral torsional buckling

$$\begin{aligned} \omega_{2} &= 1 \quad\text{(A beam under uniform moment)} \\ L &= 6000 \quad\text{(Unbraced length of beam, in mm)} \\ E &= 200000 \quad\text{(Elastic modulus, in MPa)} \\ I_{y} &= 160 \times 10^{6} \quad\text{(Second moment of area about weak axis, in mm}\hat{}\text{4)} \\ G &= 77 \times 10^{3} \quad\text{(Shear modulus, in MPa)} \\ J &= 133 \times 10^{3} \quad\text{(Polar moment of area, in mm}\hat{}\text{3)} \\ C_{w} &= 200 \times 10^{9} \quad\text{(Warping constant)} \end{aligned}$$

&nbsp;

$$\begin{aligned} M_{u} &= \frac{\omega_{2} \cdot \pi}{L} \cdot \sqrt{E \cdot I_{y} \cdot G \cdot J + \left(\frac{\pi \cdot E}{L}\right)^{2} \cdot I_{y} \cdot C_{w}} \\ &= \frac{1 \cdot 3.1416}{6000} \cdot \sqrt{200000 \cdot 1.6 \times 10^{8} \cdot 77000 \cdot 1.33 \times 10^{5} + \left(\frac{3.1416 \cdot 200000}{6000}\right)^{2} \cdot 1.6 \times 10^{8} \cdot 2 \times 10^{11}} \\ &= 4.3134 \times 10^{8} \quad\text{(A long equation)} \end{aligned}$$

&nbsp;

$$\begin{aligned} M_{u} &= \frac{\omega_{2} \cdot \pi}{L} \cdot \sqrt{E \cdot I_{y} \cdot G \cdot J + \left(\frac{\pi \cdot E}{L}\right)^{2} \cdot I_{y} \cdot C_{w}} = \frac{1 \cdot 3.1416}{6000} \cdot \sqrt{200000 \cdot 1.6 \times 10^{8} \cdot 77000 \cdot 1.33 \times 10^{5} + \left(\frac{3.1416 \cdot 200000}{6000}\right)^{2} \cdot 1.6 \times 10^{8} \cdot 2 \times 10^{11}} = 4.3134 \times 10^{8} \quad\text{(A long equation)} \end{aligned}$$

## Steel section class checks

The purpose of this demo is to show nested if/elif/else statements

$$\begin{aligned} b_{w} &= 200 \quad\text{(mm)} \\ h_{w} &= 310 \quad\text{(mm)} \\ t_{f} &= 10 \quad\text{(mm)} \\ t_{w} &= 6 \quad\text{(mm)} \\ F_{y} &= 350 \quad\text{(MPa)} \end{aligned}$$

Since $\bigl(\frac{b_{w}}{2 \cdot t_{f}} \le \frac{200}{\sqrt{F_{y}}}\bigr) \rightarrow \bigl(\frac{200}{2 \cdot 10} \le \frac{200}{\sqrt{350}}\bigr)$ is True:

> Since $\bigl(\frac{h_{w}}{t_{w}} \le \frac{2400}{\sqrt{F_{y}}}\bigr) \rightarrow \bigl(\frac{310}{6} \le \frac{2400}{\sqrt{350}}\bigr)$ is True:
>
> > $$\begin{aligned} \mathrm{class}_{\mathrm{section}} &= 3 \end{aligned}$$

## Iteration using for-loops

$$\begin{aligned} \mathrm{vals}_{x} &= [1, 2, 3, 4, 5] \\ \mathrm{vals}_{y} &= [5, 4, 3, 2, 1] \end{aligned}$$

&nbsp;

Iterating over each $\mathrm{val}_{x}$ in $\mathrm{vals}_{x}$:

> Iterating over each $\mathrm{val}_{y}$ in $\mathrm{vals}_{y}$:
>
> > $$\begin{aligned} \mathrm{value}_{\mathrm{computed}} &= \operatorname{degrees}\left(\arctan\left(\frac{\mathrm{val}_{y}}{\mathrm{val}_{x}}\right)\right) = \operatorname{degrees}\left(\arctan\left(\frac{1}{5}\right)\right) = 11.31 \\ \mathrm{acc}.\mathrm{append}\left(\mathrm{value}_{\mathrm{computed}}\right) &= \mathrm{acc}.\mathrm{append}\left(11.31\right) \end{aligned}$$

$$\begin{aligned} \mathrm{acc} &= [78.69, 75.964, 71.565, \ldots, 30.964, 21.801, 11.31] \end{aligned}$$

## Logical, identity and membership operators

This section demonstrates the `and`, `or`, `not`, `is`, and `in` operators. The `and`/`or` operators render with their operands spaced, while a nested `or` inside an `and` is parenthesized to preserve precedence.

$$\begin{aligned} \mathrm{temp} &= 75 \quad\text{(Measured temperature, deg C)} \\ \mathrm{temp}_{\mathrm{min}} &= 40 \quad\text{(Minimum operating temperature, deg C)} \\ \mathrm{temp}_{\mathrm{max}} &= 120 \quad\text{(Maximum operating temperature, deg C)} \\ \mathrm{materials} &= [\text{"steel"}, \text{"concrete"}, \text{"timber"}] \\ \mathrm{material} &= \text{"steel"} \\ \mathrm{override} &= \mathrm{None} \\ \mathrm{in}_{\mathrm{range}} &= \mathrm{temp}_{\mathrm{min}} \lt \mathrm{temp} \;\mathrm{and}\; \mathrm{temp} \lt \mathrm{temp}_{\mathrm{max}} = 40 \lt 75 \;\mathrm{and}\; 75 \lt 120 = \mathrm{True} \quad\text{(Within the operating range)} \\ \mathrm{is}_{\mathrm{extreme}} &= \mathrm{temp} \lt \mathrm{temp}_{\mathrm{min}} \;\mathrm{or}\; \mathrm{temp} \gt \mathrm{temp}_{\mathrm{max}} = 75 \lt 40 \;\mathrm{or}\; 75 \gt 120 = \mathrm{False} \quad\text{(Outside the operating range)} \\ \mathrm{not}_{\mathrm{frozen}} &= \mathrm{not}\;\left(\mathrm{temp} \lt 0\right) = \mathrm{not}\;\left(75 \lt 0\right) = \mathrm{True} \quad\text{(Above freezing)} \\ \mathrm{material}_{\mathrm{ok}} &= \mathrm{material} \in \mathrm{materials} = \text{"steel"} \in [\text{"steel"}, \text{"concrete"}, \text{"timber"}] = \mathrm{True} \quad\text{(Material is recognised)} \\ \mathrm{material}_{\mathrm{missing}} &= \mathrm{material} \notin \mathrm{materials} = \text{"steel"} \notin [\text{"steel"}, \text{"concrete"}, \text{"timber"}] = \mathrm{False} \\ \mathrm{no}_{\mathrm{override}} &= \mathrm{override} \;\mathrm{is}\; \mathrm{None} = \mathrm{None} \;\mathrm{is}\; \mathrm{None} = \mathrm{True} \quad\text{(No manual override was set)} \\ \mathrm{has}_{\mathrm{override}} &= \mathrm{override} \;\mathrm{is\ not}\; \mathrm{None} = \mathrm{None} \;\mathrm{is\ not}\; \mathrm{None} = \mathrm{False} \\ \mathrm{combined} &= \mathrm{in}_{\mathrm{range}} \;\mathrm{and}\; \left(\mathrm{is}_{\mathrm{extreme}} \;\mathrm{or}\; \mathrm{not}_{\mathrm{frozen}}\right) = \mathrm{True} \;\mathrm{and}\; \left(\mathrm{False} \;\mathrm{or}\; \mathrm{True}\right) = \mathrm{True} \quad\text{(Precedence: }\texttt{or}\text{ is parenthesized)} \end{aligned}$$

Since $\bigl(\mathrm{temp}_{\mathrm{min}} \lt \mathrm{temp} \lt \mathrm{temp}_{\mathrm{max}} \;\mathrm{and}\; \mathrm{material} \in \mathrm{materials}\bigr) \rightarrow \bigl(40 \lt 75 \lt 120 \;\mathrm{and}\; \text{"steel"} \in [\text{"steel"}, \text{"concrete"}, \text{"timber"}]\bigr)$ is True:

> $$\begin{aligned} \mathrm{section}_{\mathrm{check}} &= 1 \end{aligned}$$

$$\begin{aligned} a_{\mathrm{dictionary}} &= \{\text{"cat"}\colon 1, \text{"hat"}\colon 2, \text{"bat"}\colon 3.1416\} \\ a_{\mathrm{tuple}} &= (\text{"string"}, 1, 42, 3 + 4j) \end{aligned}$$
