#MCP GitHub Assistant

MCP - Model Context Protocol
 - mcp is a standard way for ai models to connect with tools,data and systems.

 - connector between ai and outside world.
 -bridge tahat ai lets talk to apps, files and services.

 normally ai cant access files, apps,services, mcp solves this issue -
      > one standard
      > plug anyhting easily
      > reusable connections

      working:

      user->ai->mcp->tool->response

      user ->claude(ai)-> mcp client-> mcp server-> github api



      ## Features:
       >create GitHub repositories 
       >Push files to repositories
       >list repositories and files
       >Read files from repositories
       >read file content
       >check if repo exists or not
       >multi-tool calling
       >conversation memory
       >web UI with quick buttons
       >smart file search ( case insensitive)
       >clean success/error messages
       >uploading file to existing repo
       >deleting repo
       >pushing entire folder at once
       >create branches
       

      ##setup

      1.install dependencies:
      pip install -r requirements.txt

      2. set github token:
      export GITHUB_TOKEN+your_token_here

      3. run:
      python server.py // this is in terminal 

      