# TermStimation - (Multiplayer) Planning-Poker in the terminal

> Term(inal E)stimation

No client app is needed, only `ssh`/`telnet`.

A quick and dirty approach, so you don't have to use external apps and search the web for a
registration-free lightweight tool.

What can you do with this? Have rounds of blind estimations - nothing more nothing less

https://github.com/gaborvecsei/TermStimation-Planning-Poker/assets/18753533/b2581c17-842e-4b8b-830c-11d68c7b452e

## Usage

- `pythons server.py --port 2222`
  - Start the server anywhere that can be accessed by everyone in your team
- `telnet <SERVER_IP> 2222`

Different roles & actions:
- **Host user** - can be anyone who creates a new room (a unique room name that is not allocated already)
  - The host user has an extra action during estimation:
    - `terminate`: this will terminate the room
- **Normal user** - anyone who joins an already existing room
  - During estimation there is an extra command with which the suer can leave the room: `bye` or `exit`

