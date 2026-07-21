# 从 AIR 拷贝可复用文件到 agentinsight-docbot
$src = 'd:\Projects\Entrepreneurship\AIProjects\AgentInsightAgents\agentinsight-researcher'
$dst = 'd:\Projects\Entrepreneurship\AIProjects\AgentInsightAgents\agentinsight-docbot'

# 创建目标目录结构
$dirs = @(
    "$dst\src\common",
    "$dst\src\rag",
    "$dst\src\llm",
    "$dst\src\memory",
    "$dst\src\observability",
    "$dst\src\api",
    "$dst\src\skills\researcher",
    "$dst\src\tools",
    "$dst\src\config\docbot",
    "$dst\src\agents\docbot",
    "$dst\src\skills\docbot",
    "$dst\src\graph",
    "$dst\evals",
    "$dst\static",
    "$dst\tests"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

# 拷贝整个目录
Copy-Item -Recurse -Force "$src\src\common\*" "$dst\src\common"
Copy-Item -Recurse -Force "$src\src\rag\*" "$dst\src\rag"
Copy-Item -Recurse -Force "$src\src\llm\*" "$dst\src\llm"
Copy-Item -Recurse -Force "$src\src\memory\*" "$dst\src\memory"
Copy-Item -Recurse -Force "$src\src\observability\*" "$dst\src\observability"

# 拷贝单个文件
$files = @(
    @{src="$src\src\api\routes.py"; dst="$dst\src\api\routes.py"},
    @{src="$src\src\api\middleware.py"; dst="$dst\src\api\middleware.py"},
    @{src="$src\src\api\session_routes.py"; dst="$dst\src\api\session_routes.py"},
    @{src="$src\src\api\ip_user_resolver.py"; dst="$dst\src\api\ip_user_resolver.py"},
    @{src="$src\src\api\__init__.py"; dst="$dst\src\api\__init__.py"},
    @{src="$src\src\skills\researcher\publisher.py"; dst="$dst\src\skills\researcher\publisher.py"},
    @{src="$src\src\skills\researcher\image_generator.py"; dst="$dst\src\skills\researcher\image_generator.py"},
    @{src="$src\src\skills\__init__.py"; dst="$dst\src\skills\__init__.py"},
    @{src="$src\src\skills\researcher\__init__.py"; dst="$dst\src\skills\researcher\__init__.py"},
    @{src="$src\src\__init__.py"; dst="$dst\src\__init__.py"},
    @{src="$src\src\config\__init__.py"; dst="$dst\src\config\__init__.py"},
    @{src="$src\src\config\settings.py"; dst="$dst\src\config\settings.py"},
    @{src="$src\server.py"; dst="$dst\server.py"},
    @{src="$src\requirements.txt"; dst="$dst\requirements.txt"},
    @{src="$src\requirements-dev.txt"; dst="$dst\requirements-dev.txt"},
    @{src="$src\.env.template"; dst="$dst\.env.template"},
    @{src="$src\pyproject.toml"; dst="$dst\pyproject.toml"},
    @{src="$src\Dockerfile"; dst="$dst\Dockerfile"},
    @{src="$src\docker-compose.yml"; dst="$dst\docker-compose.yml"},
    @{src="$src\docker-build.sh"; dst="$dst\docker-build.sh"},
    @{src="$src\static\index.html"; dst="$dst\static\index.html"}
)
foreach ($f in $files) {
    if (Test-Path $f.src) {
        Copy-Item -Force $f.src $f.dst
        Write-Host "Copied: $($f.dst)"
    } else {
        Write-Host "WARN not found: $($f.src)"
    }
}

Write-Host "`n=== AIR files copied successfully ==="
