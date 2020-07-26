import os
import pathlib
import shutil

import nbconvert

HERE = pathlib.Path(__file__).resolve()
TEMPLATES = HERE.parent / "templates"
AVAILABLE_TEMPLATES = TEMPLATES.glob("*.tplx")
NBCONVERT_TEMPLATES_DIR = pathlib.Path(nbconvert.__file__).resolve().parent / "templates" / "latex"

def install_by_swap(swap_in: str = "", swap_out: str = "article.tplx", restore: bool = False) -> None:
    """
    Replaces the file 'swap_out' with the file 'swap_in'. The swapped in
    file will be copied to the location of 'swap_out' and be given its file name.
    The swapped out file is simply renamed with the string "_swapped" at the end so that
    it can be restored.

    Parameters:

    'swap_in' - The name of the template file to swap in. 
    If left as "", then install by swap will print the list of available
    .tplx files located in the handcalcs/templates directory

    'swap_out' - The name of the template file in the nbconvert/templates/latex directory
    to swap_out. Default is "article.tplx", the default template for nbconvert.

    'restore' - Default is False. If True, the nbconvert templates directory is searched for
    a file with the name of 'swap_out' + "_swapped.tplx". If found, then any file in the 
    templates directory that has the name of 'swap_out' is deleted and the file with the 
    name 'swap_out' + "_swapped.tplx" is renamed to just the name of 'swap_out'.
    """
    if not swap_in and not restore: 
        print("Available templates: \n", [template.name for template in AVAILABLE_TEMPLATES])
        return

    swapped_name = pathlib.Path(swap_out).stem + "_swapped" + pathlib.Path(swap_out).suffix
    if restore and (NBCONVERT_TEMPLATES_DIR / swapped_name).exists():
        if (NBCONVERT_TEMPLATES_DIR / swap_out).exists(): 
            os.remove(NBCONVERT_TEMPLATES_DIR / swap_out)
        os.rename(NBCONVERT_TEMPLATES_DIR / swapped_name, NBCONVERT_TEMPLATES_DIR / swap_out)
        print(f"{NBCONVERT_TEMPLATES_DIR / swap_out}\n-was deleted, and replaced with-\n{NBCONVERT_TEMPLATES_DIR / swapped_name}")
        return
    elif restore:
        print(f"Cannot restore. No nbconvert template exists with name {swapped_name}")
        return

    if (NBCONVERT_TEMPLATES_DIR / swapped_name).exists() and swap_in:
        print(f"Cannot install {swap_in} because {swapped_name} has not been restored.\n Run this function again with restore=True first.")
    try:
        os.rename(NBCONVERT_TEMPLATES_DIR / swap_out, NBCONVERT_TEMPLATES_DIR / swapped_name)
    except FileExistsError:
        os.replace(NBCONVERT_TEMPLATES_DIR / swap_out, NBCONVERT_TEMPLATES_DIR / swapped_name)

    incoming_template = TEMPLATES / swap_in
    shutil.copyfile(incoming_template, NBCONVERT_TEMPLATES_DIR / swap_out)
    success_msg = f"{NBCONVERT_TEMPLATES_DIR / swap_out}\n -is now- \n{NBCONVERT_TEMPLATES_DIR / swapped_name}.\n\n{incoming_template}\n -is now- \n{NBCONVERT_TEMPLATES_DIR / swap_out}."
    print(success_msg)
    