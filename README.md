## 개발자를 위한 MCP 가이드



### fastmcp install 명령어 입력시 주의사항

 1. fastmcp install <path> (버전 2.10.3 이전까지)
FastMCP 버전 2.10.3 이전까지는 **클라이언트 이름(예: claude-desktop)**을 명시하지 않고도 단순히 fastmcp install <파일경로> 명령으로 서버 설치가 가능했습니다.

이 명령어는 설치 대상이 Claude Desktop인 경우에도 클라이언트를 따로 지정하지 않고 사용할 수 있었습니다.

```
fastmcp install server.py
```

2. fastmcp install claude-desktop <path> (버전 2.10.3 이후)
버전 2.10.3부터는 여러 클라이언트(예: Claude Desktop 외에 다른 MCP 클라이언트)가 지원되면서, 설치 시 어떤 클라이언트용 서버인지 명확히 지정해야 합니다.

따라서, 설치 명령에 클라이언트 이름을 포함하는 것이 필수가 되었습니다.

```
fastmcp install claude-desktop server.py
```

또한, fastmcp install 명령은 이제 클라이언트 명을 반드시 포함해야 하며, 포함하지 않으면 오류가 발생합니다.

