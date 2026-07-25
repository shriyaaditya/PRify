import logging
from typing import List, Dict, Any, Optional
from tree_sitter import Parser, Language, Node
import tree_sitter_typescript as tstypescript

from app.parsers.tree_sitter.parser import BaseLanguageParser
from app.parsers.tree_sitter.models import (
    ParsedFile, ClassMetadata, FunctionMetadata, MethodMetadata,
    ImportMetadata, CommentMetadata, Symbol
)

logger = logging.getLogger(__name__)

class TypeScriptParser(BaseLanguageParser):
    def __init__(self, is_tsx: bool = False):
        self.is_tsx = is_tsx
        if is_tsx:
            self.language = Language(tstypescript.language_tsx())
        else:
            self.language = Language(tstypescript.language_typescript())
        self.parser = Parser(self.language)

    def parse(self, filepath: str, source_code: bytes) -> ParsedFile:
        tree = self.parser.parse(source_code)
        root_node = tree.root_node

        classes: List[ClassMetadata] = []
        functions: List[FunctionMetadata] = []
        imports: List[ImportMetadata] = []
        comments: List[CommentMetadata] = []
        symbols: List[Symbol] = []

        code_str = source_code.decode("utf-8", errors="ignore")
        lines = code_str.splitlines()
        total_lines = len(lines)

        class_map: Dict[str, ClassMetadata] = {}

        def get_decorators(node: Node) -> List[str]:
            decorators = []
            if hasattr(node, "children"):
                for child in node.children:
                    if child.type == "decorator":
                        dec_text = code_str[child.start_byte:child.end_byte].strip()
                        decorators.append(dec_text)
            return decorators

        def traverse(node: Node, parent_class: Optional[str] = None):
            # 1. Imports
            if node.type == "import_statement":
                text = code_str[node.start_byte:node.end_byte].strip()
                imports.append(ImportMetadata(
                    name=text,
                    line_number=node.start_point[0] + 1
                ))

            # 2. Comments
            elif node.type == "comment":
                text = code_str[node.start_byte:node.end_byte].strip()
                comments.append(CommentMetadata(
                    content=text,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1
                ))

            # 3. Class declaration
            elif node.type in ("class_declaration", "class_expression"):
                name_node = node.child_by_field_name("name")
                class_name = code_str[name_node.start_byte:name_node.end_byte] if name_node else "UnknownClass"
                
                class_start = node.start_point[0] + 1
                class_end = node.end_point[0] + 1
                decorators = get_decorators(node)

                class_meta = ClassMetadata(
                    name=class_name,
                    start_line=class_start,
                    end_line=class_end,
                    decorators=decorators,
                    methods=[]
                )
                classes.append(class_meta)
                class_map[class_name] = class_meta

                symbols.append(Symbol(
                    name=class_name,
                    kind="class",
                    start_line=class_start,
                    end_line=class_end
                ))

                for child in node.children:
                    traverse(child, parent_class=class_name)
                return

            # 4. Method definition
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                method_name = code_str[name_node.start_byte:name_node.end_byte] if name_node else "UnknownMethod"
                
                m_start = node.start_point[0] + 1
                m_end = node.end_point[0] + 1
                decorators = get_decorators(node)

                if parent_class and parent_class in class_map:
                    class_map[parent_class].methods.append(MethodMetadata(
                        name=method_name,
                        start_line=m_start,
                        end_line=m_end,
                        decorators=decorators
                    ))
                    symbols.append(Symbol(
                        name=method_name,
                        kind="method",
                        start_line=m_start,
                        end_line=m_end,
                        parent=parent_class
                    ))

            # 5. Function declarations
            elif node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                func_name = code_str[name_node.start_byte:name_node.end_byte] if name_node else "UnknownFunction"
                
                f_start = node.start_point[0] + 1
                f_end = node.end_point[0] + 1
                decorators = get_decorators(node)

                functions.append(FunctionMetadata(
                    name=func_name,
                    start_line=f_start,
                    end_line=f_end,
                    decorators=decorators,
                    is_method=False
                ))

                symbols.append(Symbol(
                    name=func_name,
                    kind="function",
                    start_line=f_start,
                    end_line=f_end
                ))

            # 6. Interfaces
            elif node.type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    iface_name = code_str[name_node.start_byte:name_node.end_byte]
                    symbols.append(Symbol(
                        name=iface_name,
                        kind="interface",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1
                    ))

            # 7. Enums
            elif node.type == "enum_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    enum_name = code_str[name_node.start_byte:name_node.end_byte]
                    symbols.append(Symbol(
                        name=enum_name,
                        kind="enum",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1
                    ))

            # 8. Exports
            elif node.type == "export_statement":
                for child in node.children:
                    traverse(child, parent_class)
                return

            # Recurse children
            for child in node.children:
                traverse(child, parent_class)

        traverse(root_node)

        lang_label = "typescript-react" if self.is_tsx else "typescript"
        statistics = {
            "lines": total_lines,
            "classes": len(classes),
            "functions": len(functions) + sum(len(c.methods) for c in classes)
        }

        return ParsedFile(
            filepath=filepath,
            language=lang_label,
            classes=classes,
            functions=functions,
            imports=imports,
            comments=comments,
            statistics=statistics,
            symbols=symbols
        )
