"""Empty language scaffolds shown to players before they write a solution."""

BASIC_STARTER_CODE = {
    "cpp": (
        "#include <bits/stdc++.h>\n"
        "using namespace std;\n\n"
        "int main() {\n"
        "    ios::sync_with_stdio(false);\n"
        "    cin.tie(nullptr);\n\n"
        "    // TODO: Read input and write your solution.\n"
        "    return 0;\n"
        "}\n"
    ),
    "python": (
        "import sys\n\n"
        "def solve():\n"
        "    data = sys.stdin.read().split()\n"
        "    # TODO: Write your solution.\n\n"
        "if __name__ == \"__main__\":\n"
        "    solve()\n"
    ),
    "java": (
        "import java.util.*;\n\n"
        "public class Main {\n"
        "    public static void main(String[] args) {\n"
        "        Scanner sc = new Scanner(System.in);\n"
        "        // TODO: Read input and write your solution.\n"
        "    }\n"
        "}\n"
    ),
}
