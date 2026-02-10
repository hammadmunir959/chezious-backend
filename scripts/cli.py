#!/usr/bin/env python3
"""CheziousBot CLI - Interactive chat client with streaming"""

import asyncio
import signal
import sys
import httpx
from uuid import UUID, uuid4



import os
from dotenv import load_dotenv

load_dotenv()

API_BASE = "http://localhost:8000/api/v1"
API_KEY = os.getenv("API_KEY", "")

if not API_KEY:
    print("⚠️  Warning: API_KEY not found in .env file")


async def stream_chat(
    client: httpx.AsyncClient,
    session_id: UUID,
    message: str,
    user_id: str,
) -> None:
    """Send a message and stream the response."""
    import json
    
    print("\n🤖 ", end="", flush=True)

    try:
        async with client.stream(
            "POST",
            f"{API_BASE}/chat",
            json={"session_id": str(session_id), "message": message},
            headers={
                "X-User-ID": user_id,
                "X-API-Key": API_KEY,
            },
            timeout=60.0,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line:
                    continue

                # Parse SSE format
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    if event_type == "done":
                        break
                    continue

                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data:
                        try:
                            parsed = json.loads(data)
                            if "token" in parsed:
                                print(parsed["token"], end="", flush=True)
                            elif "error" in parsed:
                                print(f"\n❌ Error: {parsed['error']}")
                        except json.JSONDecodeError:
                            pass
    except asyncio.CancelledError:
        print("\n[Cancelled]")
        raise

    print()  # New line after response


def generate_session_id() -> UUID:
    """Generate a new session ID locally."""
    return uuid4()


async def main():
    """Main CLI loop."""
    print("=" * 50)
    print("🍕 Welcome to CheziousBot CLI!")
    print("=" * 50)
    print("\nType your message and press Enter.")
    print("Commands: /new (new session), /quit (exit)\n")

    print("Commands: /new (new session), /quit (exit)\n")

    async with httpx.AsyncClient() as client:
        # Get user info loop
        while True:
            try:
                username = input("Enter your unique username (user_id): ").strip()
                if not username:
                    print("Username cannot be empty.")
                    continue
                
                name = input("Enter your display name: ").strip() or username
                
                print("\nCities: Lahore, Islamabad, Rawalpindi, Peshawar, Kasur, Mardan, Sahiwal")
                city = input("Enter your city (optional): ").strip() or None
                
                user_id = username
                
                print(f"\nHello, {name}! Registering...\n")
                
                # Try to create user
                try:
                    payload = {"user_id": user_id, "name": name}
                    if city:
                        payload["city"] = city
                    
                    response = await client.post(
                        f"{API_BASE}/users/", 
                        json=payload,
                        headers={"X-API-Key": API_KEY}
                    )
                    
                    if response.status_code == 409:
                        print(f"ℹ️  Username '{user_id}' found. Logging in...\n")
                        break
                        
                    response.raise_for_status()
                    print("✅ User registered successfully")
                    break  # Exit loop on success
                    
                except httpx.HTTPError as e:
                    print(f"❌ Failed to connect: {e}")
                    print("Make sure the server is running: uvicorn app.main:app --reload")
                    return

            except (KeyboardInterrupt, EOFError):
                print("\n\n👋 Goodbye!")
                return

        # Generate session ID locally (lazy creation on first message)
        session_id = generate_session_id()
        print(f"✅ Session ready: {str(session_id)[:8]}...\n")

        while True:
            try:
                user_input = input(f"\n{user_id} > ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "/quit":
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() == "/new":
                    session_id = generate_session_id()
                    print(f"\n✅ New session ready: {str(session_id)[:8]}...\n")
                    continue

                await stream_chat(client, session_id, user_input, user_id)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
            except asyncio.CancelledError:
                print("\n\n👋 Cancelled!")
                break
            except httpx.HTTPError as e:
                print(f"\n❌ API Error: {e}")
            except Exception as e:
                print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
