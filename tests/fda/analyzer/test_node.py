from __future__ import annotations

import ast
from pathlib import Path

from fda.node.wrapper import ASTNodeWrapper


class TestASTNodeWrapper:
    """Tests for ASTNodeWrapper class."""

    def test_init_with_function_def(self) -> None:
        func_node = ast.FunctionDef(name="test_func", args=ast.arguments(), body=[])
        filepath = Path("/home/user/project/module.py")

        wrapper = ASTNodeWrapper(func_node, filepath)

        assert wrapper.ast_node == func_node
        assert wrapper.ast_type == ast.FunctionDef
        assert wrapper.ast_name == "test_func"
        assert wrapper.filepath == Path("/home/user/project/module")
        assert wrapper.parent is None
        assert len(wrapper.functions) == 1
        assert wrapper.functions[0] == wrapper
        assert len(wrapper.classes) == 0

    def test_init_with_class_def(self) -> None:
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        filepath = Path("/home/user/project/module.py")

        wrapper = ASTNodeWrapper(class_node, filepath)

        assert wrapper.ast_name == "MyClass"
        assert len(wrapper.classes) == 1
        assert wrapper.classes[0] == wrapper
        assert len(wrapper.functions) == 0

    def test_init_with_parent(self) -> None:
        """Test initialization with a parent node."""
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        func_node = ast.FunctionDef(name="method", args=ast.arguments(), body=[])
        filepath = Path("/home/user/project/module.py")

        class_wrapper = ASTNodeWrapper(class_node, filepath)
        method_wrapper = ASTNodeWrapper(func_node, filepath, parent=class_wrapper)

        assert method_wrapper.parent == class_wrapper
        assert len(method_wrapper.classes) == 1
        assert method_wrapper.classes[0] == class_wrapper
        assert len(method_wrapper.functions) == 1
        assert method_wrapper.functions[0] == method_wrapper

    def test_get_name_function_def(self) -> None:
        func_node = ast.FunctionDef(name="my_function", args=ast.arguments(), body=[])
        wrapper = ASTNodeWrapper(func_node, Path("/test/file.py"))

        assert wrapper.get_name() == "my_function"

    def test_get_name_class_def(self) -> None:
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        wrapper = ASTNodeWrapper(class_node, Path("/test/file.py"))

        assert wrapper.get_name() == "MyClass"

    def test_get_name_name_node(self) -> None:
        name_node = ast.Name(id="variable", ctx=ast.Load())
        wrapper = ASTNodeWrapper(name_node, Path("/test/file.py"))

        assert wrapper.get_name() == "variable"

    def test_get_name_call_with_name_func(self) -> None:
        call_node = ast.Call(func=ast.Name(id="print", ctx=ast.Load()), args=[], keywords=[])
        wrapper = ASTNodeWrapper(call_node, Path("/test/file.py"))

        assert wrapper.get_name() == "print"

    def test_get_name_call_with_attribute_func(self) -> None:
        call_node = ast.Call(
            func=ast.Attribute(value=ast.Name(id="obj", ctx=ast.Load()), attr="method", ctx=ast.Load()),
            args=[],
            keywords=[],
        )
        wrapper = ASTNodeWrapper(call_node, Path("/test/file.py"))

        assert wrapper.get_name() == "method"

    def test_get_name_fallback(self) -> None:
        module_node = ast.Module(body=[], type_ignores=[])
        wrapper = ASTNodeWrapper(module_node, Path("/test/file.py"))

        assert wrapper.get_name() == "Module"

    def test_get_chain_single_node(self) -> None:
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        wrapper = ASTNodeWrapper(func_node, Path("/test/file.py"))

        chain = wrapper.get_chain()

        assert len(chain) == 1
        assert chain[0] == wrapper

    def test_get_chain_multiple_nodes(self) -> None:
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        func_node = ast.FunctionDef(name="method", args=ast.arguments(), body=[])
        call_node = ast.Call(func=ast.Name(id="helper", ctx=ast.Load()), args=[], keywords=[])
        filepath = Path("/test/file.py")

        class_wrapper = ASTNodeWrapper(class_node, filepath)
        method_wrapper = ASTNodeWrapper(func_node, filepath, parent=class_wrapper)
        call_wrapper = ASTNodeWrapper(call_node, filepath, parent=method_wrapper)

        chain = call_wrapper.get_chain()

        assert len(chain) == 3
        assert chain[0] == class_wrapper
        assert chain[1] == method_wrapper
        assert chain[2] == call_wrapper

    def test_full_name_single_node(self) -> None:
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        wrapper = ASTNodeWrapper(func_node, Path("/test/file.py"))

        assert wrapper.full_name == "func"

    def test_full_name_nested_nodes(self) -> None:
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        func_node = ast.FunctionDef(name="method", args=ast.arguments(), body=[])
        filepath = Path("/test/file.py")

        class_wrapper = ASTNodeWrapper(class_node, filepath)
        method_wrapper = ASTNodeWrapper(func_node, filepath, parent=class_wrapper)

        assert method_wrapper.full_name == "MyClass.method"

    def test_full_path_single_function(self) -> None:
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        wrapper = ASTNodeWrapper(func_node, Path("/home/user/module.py"))

        assert wrapper.full_path == "/home/user/module.func"

    def test_full_path_nested_structure(self) -> None:
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        func_node = ast.FunctionDef(name="method", args=ast.arguments(), body=[])
        filepath = Path("/home/user/module.py")

        class_wrapper = ASTNodeWrapper(class_node, filepath)
        method_wrapper = ASTNodeWrapper(func_node, filepath, parent=class_wrapper)

        assert method_wrapper.full_path == "/home/user/module.MyClass.method"

    def test_full_path_with_call(self) -> None:
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        call_node = ast.Call(func=ast.Name(id="helper", ctx=ast.Load()), args=[], keywords=[])
        filepath = Path("/test/file.py")

        func_wrapper = ASTNodeWrapper(func_node, filepath)
        call_wrapper = ASTNodeWrapper(call_node, filepath, parent=func_wrapper)

        assert call_wrapper.full_path == "/test/file.func.helper"

    def test_full_path_excludes_other_nodes(self) -> None:
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        name_node = ast.Name(id="var", ctx=ast.Load())
        filepath = Path("/test/file.py")

        func_wrapper = ASTNodeWrapper(func_node, filepath)
        name_wrapper = ASTNodeWrapper(name_node, filepath, parent=func_wrapper)

        assert name_wrapper.full_path == "/test/file.func"

    def test_get_functions_no_parent(self) -> None:
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        wrapper = ASTNodeWrapper(func_node, Path("/test/file.py"))

        functions = wrapper.get_functions(None)

        assert len(functions) == 1
        assert functions[0] == wrapper

    def test_get_functions_with_parent(self) -> None:
        func1_node = ast.FunctionDef(name="func1", args=ast.arguments(), body=[])
        func2_node = ast.FunctionDef(name="func2", args=ast.arguments(), body=[])
        filepath = Path("/test/file.py")

        func1_wrapper = ASTNodeWrapper(func1_node, filepath)
        func2_wrapper = ASTNodeWrapper(func2_node, filepath, parent=func1_wrapper)

        assert len(func2_wrapper.functions) == 2
        assert func1_wrapper in func2_wrapper.functions
        assert func2_wrapper in func2_wrapper.functions

    def test_get_functions_non_function_node(self):
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        wrapper = ASTNodeWrapper(class_node, Path("/test/file.py"))

        functions = wrapper.get_functions(None)

        assert len(functions) == 0

    def test_get_classes_no_parent(self) -> None:
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        wrapper = ASTNodeWrapper(class_node, Path("/test/file.py"))

        classes = wrapper.get_classes(None)

        assert len(classes) == 1
        assert classes[0] == wrapper

    def test_get_classes_with_parent(self) -> None:
        class1_node = ast.ClassDef(name="Class1", bases=[], keywords=[], body=[])
        class2_node = ast.ClassDef(name="Class2", bases=[], keywords=[], body=[])
        filepath = Path("/test/file.py")

        class1_wrapper = ASTNodeWrapper(class1_node, filepath)
        class2_wrapper = ASTNodeWrapper(class2_node, filepath, parent=class1_wrapper)

        assert len(class2_wrapper.classes) == 2
        assert class1_wrapper in class2_wrapper.classes
        assert class2_wrapper in class2_wrapper.classes

    def test_get_classes_non_class_node(self):
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        wrapper = ASTNodeWrapper(func_node, Path("/test/file.py"))

        classes = wrapper.get_classes(None)

        assert len(classes) == 0

    def test_add_function(self) -> None:
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        func_node = ast.FunctionDef(name="method", args=ast.arguments(), body=[])
        filepath = Path("/test/file.py")

        class_wrapper = ASTNodeWrapper(class_node, filepath)
        func_wrapper = ASTNodeWrapper(func_node, filepath)

        initial_count = len(class_wrapper.functions)
        class_wrapper.add_function(func_wrapper)

        assert len(class_wrapper.functions) == initial_count + 1
        assert func_wrapper in class_wrapper.functions

    def test_add_class(self) -> None:
        module_node = ast.Module(body=[], type_ignores=[])
        class_node = ast.ClassDef(name="MyClass", bases=[], keywords=[], body=[])
        filepath = Path("/test/file.py")

        module_wrapper = ASTNodeWrapper(module_node, filepath)
        class_wrapper = ASTNodeWrapper(class_node, filepath)

        initial_count = len(module_wrapper.classes)
        module_wrapper.add_class(class_wrapper)

        assert len(module_wrapper.classes) == initial_count + 1
        assert class_wrapper in module_wrapper.classes

    def test_filepath_suffix_removal(self) -> None:
        func_node = ast.FunctionDef(name="func", args=ast.arguments(), body=[])
        wrapper = ASTNodeWrapper(func_node, Path("/home/user/module.py"))

        assert wrapper.filepath == Path("/home/user/module")
        assert wrapper.filepath.suffix == ""

    def test_complex_nested_structure(self) -> None:
        module_node = ast.Module(body=[], type_ignores=[])
        class_node = ast.ClassDef(name="OuterClass", bases=[], keywords=[], body=[])
        method_node = ast.FunctionDef(name="outer_method", args=ast.arguments(), body=[])
        inner_class_node = ast.ClassDef(name="InnerClass", bases=[], keywords=[], body=[])
        inner_method_node = ast.FunctionDef(name="inner_method", args=ast.arguments(), body=[])
        filepath = Path("/project/module.py")

        module_wrapper = ASTNodeWrapper(module_node, filepath)
        class_wrapper = ASTNodeWrapper(class_node, filepath, parent=module_wrapper)
        method_wrapper = ASTNodeWrapper(method_node, filepath, parent=class_wrapper)
        inner_class_wrapper = ASTNodeWrapper(inner_class_node, filepath, parent=method_wrapper)
        inner_method_wrapper = ASTNodeWrapper(inner_method_node, filepath, parent=inner_class_wrapper)

        assert inner_method_wrapper.full_name == "Module.OuterClass.outer_method.InnerClass.inner_method"
        assert inner_method_wrapper.full_path == "/project/module.OuterClass.outer_method.InnerClass.inner_method"

        chain = inner_method_wrapper.get_chain()
        assert len(chain) == 5

        assert len(inner_method_wrapper.classes) == 2
        assert class_wrapper in inner_method_wrapper.classes
        assert inner_class_wrapper in inner_method_wrapper.classes

        assert len(inner_method_wrapper.functions) == 2
        assert method_wrapper in inner_method_wrapper.functions
        assert inner_method_wrapper in inner_method_wrapper.functions
