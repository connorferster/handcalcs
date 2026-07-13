import inspect
import importlib.util
from pathlib import Path
from collections import ChainMap
import ast_comments as ast

class SourceExpander:
    """
    Manages module loading and provides the context for recursively
    expanding a call chain into a single procedure.
    """
    def __init__(self, initial_source_file=None):
        # Maps module names (e.g., 'my_module') to a dictionary 
        # of defined functions/classes {name: ast.FunctionDef/ClassDef}
        self.module_cache = {}
        
        # Maps module names to the full AST of the module
        self.ast_cache = {}

        if initial_source_file:
            self.load_module_by_path("__main__", initial_source_file)

    def _resolve_module_path(self, module_name: str) -> Path | None:
        """
        Uses importlib to find the source file path for a module 
        without executing any code.
        """
        try:
            # Look up the module specification
            spec = importlib.util.find_spec(module_name)
            if spec and spec.loader_state and spec.origin:
                # Return the path to the source file
                return Path(spec.origin)
        except (ValueError, AttributeError):
            # Handle cases where the module isn't found or is a built-in
            return None
        return None

    def load_module_by_path(self, module_name: str, file_path: Path):
        """Loads and parses a module's source code into the cache."""
        if module_name in self.module_cache:
            return

        try:
            source_code = file_path.read_text()
            module_ast: ast.Module = ast.parse(source_code, filename=str(file_path))
            self.ast_cache[module_name] = module_ast
            
            # Build the symbol table (namespace) for this module
            symbols = {}
            for node in module_ast.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols[node.name] = node
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    # A more robust system would process imports here to build 
                    # a full symbol-to-module map (e.g., my_func points to my_module)
                    self.resolve_import_and_load(node)
            
            self.module_cache[module_name] = symbols
            print(f"Loaded and cached module: {module_name}")

        except FileNotFoundError:
            print(f"Error: Source file not found for {module_name} at {file_path}")
        except SyntaxError as e:
            print(f"Error: Syntax error in {module_name}: {e}")

    def resolve_import_and_load(self, import_node: ast.Import | ast.ImportFrom):
        """Recursively resolves imported modules and loads them."""
        
        if isinstance(import_node, ast.Import):
            for alias in import_node.names:
                module_name = alias.name
                path = self._resolve_module_path(module_name)
                if path:
                    # Load the module, using the original name (e.g., 'my_module')
                    self.load_module_by_path(module_name, path)
        
        # Logic for ast.ImportFrom is similar but tracks specific names being imported

    def expand_call(self, call_node: ast.Call, current_module_name: str):
        """
        The core recursive function: locates the definition and expands its body.
        
        NOTE: This is heavily simplified for illustration.
        """
        func_name = None
        
        # 1. Handle Attribute (e.g., my_module.my_func)
        if isinstance(call_node.func, ast.Attribute):
            module_alias = call_node.func.value.id
            func_name = call_node.func.attr
            
            # In a real scenario, you'd look up what module 'module_alias' refers to
            # We'll simplify and assume the module name is the alias for now
            target_module_name = module_alias 
            
        # 2. Handle Name (e.g., different_func) - implies it's imported or defined locally
        elif isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id
            target_module_name = current_module_name
            
            # Check if it's in the current module's scope.
            if func_name not in self.module_cache.get(target_module_name, {}):
                # A robust system would check *all* imported modules in the current scope
                # to find where 'different_func' came from (my_other_module).
                # For this example, we assume we know the target:
                print(f"🚨 WARNING: '{func_name}' not found locally. Skipping full lookup.")
                return [ast.Comment(f"CALL: {func_name}(...)")]
            
        else:
            # Not a recognized call type for expansion (e.g., a function call via a variable)
            return [ast.Comment("CALL: UNEXPANDABLE")]

        # --- Recursion Step ---
        if target_module_name in self.module_cache and func_name in self.module_cache[target_module_name]:
            func_def_node = self.module_cache[target_module_name][func_name]
            
            # Process the body of the function definition
            new_procedure = []
            print(f"--- EXPANDING: {target_module_name}.{func_name} ---")
            
            # In a real solution, you'd recursively call a worker function on each stmt 
            # in func_def_node.body, handling arguments, renaming variables, etc.
            for stmt in func_def_node.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    # Recursive call on nested function calls
                    expanded_statements = self.expand_call(stmt.value, target_module_name)
                    new_procedure.extend(expanded_statements)
                else:
                    new_procedure.append(stmt) # Just copy the statement
            
            return new_procedure

        print(f"❌ ERROR: Function definition not found for {target_module_name}.{func_name}")
        return [ast.Comment(f"CALL: {target_module_name}.{func_name}(...) - Definition not loaded.")]
        
    def expand_top_level(self, initial_call_node_index: int):
        """
        Orchestrates the top-level expansion of the main script.
        """
        main_ast = self.ast_cache.get("__main__")
        if not main_ast:
            print("No main module loaded.")
            return

        # 1. Pre-scan for all imports and load necessary modules
        for node in main_ast.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self.resolve_import_and_load(node)
                
        # (This is where you'd manually load my_other_module for the simplified example)
        # Assuming you load all necessary modules before the final expansion

        # 2. Start the expansion at the target statement (the C = ... line)
        target_stmt = main_ast.body[initial_call_node_index]
        if isinstance(target_stmt, ast.Assign) and isinstance(target_stmt.value, ast.Call):
            return self.expand_call(target_stmt.value, "__main__")
        
        return []