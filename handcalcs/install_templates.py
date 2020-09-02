import os
import pathlib
import shutil
import nbconvert

__all__ = ["install_latex", "install_html"]

def install_latex(swap_in: str = "", swap_out: str = "article.tplx", restore: bool = False) -> None:
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
    to swap_out. Default is "article.tplx", the default latex template for nbconvert.

    'restore' - Default is False. If True, the nbconvert templates directory is searched for
    a file with the name of 'swap_out' + "_swapped.tplx". If found, then any file in the 
    templates directory that has the name of 'swap_out' is deleted and the file with the 
    name 'swap_out' + "_swapped.tplx" is renamed to just the name of 'swap_out'.
    """
    handcalcs_templates, nbconvert_templates_dir = retrieve_template_paths('latex')
    available_templates = handcalcs_templates.glob("*.tplx")
    if not swap_in and not restore: 
        print("Available templates: \n", [template.name for template in available_templates])
        return

    if restore:
        restore_swapped(swap_out, nbconvert_templates_dir)
        return

    swapped_name = pathlib.Path(swap_out).stem + "_swapped" + pathlib.Path(swap_out).suffix
    if (nbconvert_templates_dir / swapped_name).exists() and swap_in:
        print(f"Cannot install {swap_in} because {swapped_name} has not been restored.\n"
               "Run this function again with restore=True first.")
        return

    perform_template_swap(nbconvert_templates_dir, handcalcs_templates, swap_in, swap_out, swapped_name)
    return


def install_html(swap_in: str = "", swap_out: str = "full.tpl", restore: bool = False) -> None:
    """
    Replaces the file 'swap_out' with the file 'swap_in'. The swapped in
    file will be copied to the location of 'swap_out' and be given its file name.
    The swapped out file is simply renamed with the string "_swapped" at the end so that
    it can be restored.

    Parameters:

    'swap_in' - The name of the template file to swap in. 
    If left as "", then install by swap will print the list of available
    .tpl files located in the handcalcs/templates directory

    'swap_out' - The name of the template file in the nbconvert/templates/latex directory
    to swap_out. Default is "full.tpl", the default html template for nbconvert.

    'restore' - Default is False. If True, the nbconvert templates directory is searched for
    a file with the name of 'swap_out' + "_swapped.tpl". If found, then any file in the 
    templates directory that has the name of 'swap_out' is deleted and the file with the 
    name 'swap_out' + "_swapped.tpl" is renamed to just the name of 'swap_out'.
    """
    handcalcs_templates, nbconvert_templates_dir = retrieve_template_paths('html')
    available_templates = handcalcs_templates.glob("*.tpl")
    if not swap_in and not restore: 
        print("Available templates: \n", [template.name for template in available_templates])
        return

    if restore:
        restore_swapped(swap_out, nbconvert_templates_dir)
        return

    swapped_name = pathlib.Path(swap_out).stem + "_swapped" + pathlib.Path(swap_out).suffix
    if (nbconvert_templates_dir / swapped_name).exists() and swap_in:
        print(f"Cannot install {swap_in} because {swapped_name} has not been restored.\n"
               "Run this function again with restore=True first.")
        return

    perform_template_swap(nbconvert_templates_dir, handcalcs_templates, swap_in, swap_out, swapped_name)
    return


def perform_template_swap(nbconvert_templates_dir: pathlib.Path, handcalcs_templates: pathlib.Path, swap_in: str, swap_out: str, swapped_name: str):
    os.rename(nbconvert_templates_dir / swap_out, nbconvert_templates_dir / swapped_name)
    incoming_template = handcalcs_templates / swap_in
    shutil.copyfile(incoming_template, nbconvert_templates_dir / swap_out)
    success_msg = (f"{nbconvert_templates_dir / swap_out}\n -is now- \n{nbconvert_templates_dir / swapped_name}.\n\n"
                    f"{incoming_template}\n -is now- \n{nbconvert_templates_dir / swap_out}.")
    print(success_msg)


def retrieve_template_paths(template_type: str):
    """
    'template_type' is one of "html" or "latex"
    """
    here = pathlib.Path(__file__).resolve()
    templates = here.parent / "templates" / template_type
    nbconvert_templates_dir = pathlib.Path(nbconvert.__file__).resolve().parent / "templates" / template_type
    return templates, nbconvert_templates_dir


def restore_swapped(swap_file: pathlib.Path, nbconvert_templates_dir: pathlib.Path):
    """
    swap_file is an absolute path
    """
    swapped_name = pathlib.Path(swap_file).stem + "_swapped" + pathlib.Path(swap_file).suffix
    if (nbconvert_templates_dir / swapped_name).exists():
        if (nbconvert_templates_dir / swap_file).exists(): 
            os.remove(nbconvert_templates_dir / swap_file)
        os.rename(nbconvert_templates_dir / swapped_name, nbconvert_templates_dir / swap_file)
        print(f"{nbconvert_templates_dir / swapped_name}\n-was restored to-\n{nbconvert_templates_dir / swap_file}")
        return
    print(f"Cannot restore. No nbconvert template exists with name {swapped_name}")



        
