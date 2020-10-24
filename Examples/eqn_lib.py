from handcalcs.decorator import handcalc
from IPython.display import HTML

@handcalc(jupyter_display = True)
def NBCC2015LC(
    DL: float = 0, 
    SDL: float = 0, 
    SL: float = 0, 
    LL: float = 0, 
    WL: float= 0, 
    EL: float = 0
):
    LC1 = 1.4*DL
    LC2a = 1.25*DL + 1.5*LL
    LC2b = 1.25*DL + 1.5*LL + 0.5*SL
    LC3a = 1.25*DL + 1.5*SL
    LC3b = 1.25*DL + 1.5*SL + 0.5*LL
    

def title_block(
    name: str,
    proj: str,
    date: str,
    design: str,
    size: str = "1.5em"
):
    # This can be used to create a "title block" in your notebooks
    # before you start your calculations
    html_title = f"""
     <table style="width:100%; font-size:{size}; border:1px;">
          <tr>
            <td style="width:15%; text-align:right; font-weight:bold">Name: </td>
            <td style="width:35%; text_align:right">{name}</td>
            <td style="width:15%; text-align:right; font-weight:bold">Date: </td>
            <td style="width:35%; text_align:right">{date}</td>
          </tr>
          <tr>
            <td style="width:15%; text-align:right; font-weight:bold">Project: </td>
            <td style="width:35%; text_align:right">{proj}</td>
            <td style="width:15%; text-align:right; font-weight:bold">Design: </td>
            <td style="width:35%; text_align:right">{design}</td>
          </tr>
    </table> 
    """
    display(HTML(html_title))
    
