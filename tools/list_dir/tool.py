import os


class Tool:
    name = "list_dir"

    definition = {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Lista archivos y carpetas de un directorio local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Ruta del directorio a listar."
                    }
                },
                "required": []
            }
        }
    }

    def execute(self, path="."):
        safe_path = os.path.abspath(path)

        items = []
        for name in os.listdir(safe_path):
            full = os.path.join(safe_path, name)
            items.append({
                "name": name,
                "type": "dir" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else None
            })

        return items