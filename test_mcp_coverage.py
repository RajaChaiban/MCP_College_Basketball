#!/usr/bin/env python
"""
Comprehensive MCP Server Coverage Test
Tests all question categories to verify data retrieval
"""

import asyncio
import json
from datetime import datetime, timedelta
from cbb_mcp.services import games, rankings, stats, teams

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(category):
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{category}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_success(question, result):
    print(f"{GREEN}[OK] {question}{RESET}")
    if isinstance(result, (list, dict)):
        print(f"  Result: {json.dumps(str(result)[:100], indent=2)}...\n")
    else:
        print(f"  Result: {str(result)[:100]}...\n")

def print_error(question, error):
    print(f"{RED}[FAIL] {question}{RESET}")
    print(f"  Error: {str(error)[:100]}\n")

async def test_live_games():
    """Test live games and scores queries"""
    print_header("[LIVE GAMES & SCORES]")

    today = datetime.now().strftime("%Y-%m-%d")

    tests = [
        ("What games are happening tonight?",
         lambda: games.get_live_scores(today)),

        ("Which ranked teams are playing today?",
         lambda: games.get_live_scores(today, top25=True)),
    ]

    for question, test_func in tests:
        try:
            result = await test_func()
            if result:
                print_success(question, result)
            else:
                print_error(question, "No data returned")
        except Exception as e:
            print_error(question, e)

async def test_rankings():
    """Test rankings queries"""
    print_header("[RANKINGS & STANDINGS]")

    tests = [
        ("Who's #1 in the AP Top 25?",
         lambda: rankings.get_rankings(poll_type="ap")),

        ("Show me the ACC standings",
         lambda: rankings.get_standings(conference="ACC")),
    ]

    for question, test_func in tests:
        try:
            result = await test_func()
            if result:
                print_success(question, result)
            else:
                print_error(question, "No data returned")
        except Exception as e:
            print_error(question, e)

async def test_team_analysis():
    """Test team analysis queries"""
    print_header("[TEAM ANALYSIS]")

    tests = [
        ("Compare Alabama and Tennessee - who's stronger?",
         lambda: stats.compare_teams("Alabama", "Tennessee")),

        ("What's Gonzaga's conference record?",
         lambda: teams.get_team("Gonzaga")),
    ]

    for question, test_func in tests:
        try:
            result = await test_func()
            if result:
                print_success(question, result)
            else:
                print_error(question, "No data returned")
        except Exception as e:
            print_error(question, e)

async def test_player_stats():
    """Test player and roster queries"""
    print_header("[PLAYER & ROSTER INFO]")

    tests = [
        ("Who are the top scorers for Duke?",
         lambda: stats.get_player_stats("Duke")),

        ("Show me the roster for Kansas",
         lambda: teams.get_roster("Kansas")),

        ("Which freshmen are having breakout seasons?",
         lambda: stats.get_freshman_players("Duke")),
    ]

    for question, test_func in tests:
        try:
            result = await test_func()
            if result:
                print_success(question, result)
            else:
                print_error(question, "No data returned")
        except Exception as e:
            print_error(question, e)

async def test_stat_leaders():
    """Test statistics and trends queries"""
    print_header("[STATISTICS & TRENDS]")

    tests = [
        ("Which team has the best three-point percentage?",
         lambda: stats.get_stat_leaders("three_point_pct")),

        ("Who's leading in assists?",
         lambda: stats.get_stat_leaders("assists")),

        ("Who's leading in rebounds?",
         lambda: stats.get_stat_leaders("rebounds")),
    ]

    for question, test_func in tests:
        try:
            result = await test_func()
            if result:
                print_success(question, result)
            else:
                print_error(question, "No data returned")
        except Exception as e:
            print_error(question, e)

async def test_schedule():
    """Test schedule and upcoming queries"""
    print_header("[SCHEDULE & UPCOMING]")

    tests = [
        ("What's Duke's schedule for next week?",
         lambda: teams.get_schedule("Duke")),

        ("When is Michigan playing next?",
         lambda: teams.get_schedule("Michigan")),
    ]

    for question, test_func in tests:
        try:
            result = await test_func()
            if result:
                print_success(question, result)
            else:
                print_error(question, "No data returned")
        except Exception as e:
            print_error(question, e)

async def test_team_stats():
    """Test team statistics"""
    print_header("[TEAM STATISTICS]")

    tests = [
        ("Get Alabama stats",
         lambda: stats.get_team_stats("Alabama")),

        ("Get Tennessee stats",
         lambda: stats.get_team_stats("Tennessee")),
    ]

    for question, test_func in tests:
        try:
            result = await test_func()
            if result:
                print_success(question, result)
            else:
                print_error(question, "No data returned")
        except Exception as e:
            print_error(question, e)

async def main():
    print(f"\n{BOLD}{BLUE}CBB MCP SERVER COVERAGE TEST{RESET}")
    print(f"{BOLD}{BLUE}Testing: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

    await test_live_games()
    await test_rankings()
    await test_team_analysis()
    await test_player_stats()
    await test_stat_leaders()
    await test_schedule()
    await test_team_stats()

    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{GREEN}[DONE] Test execution completed{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

if __name__ == "__main__":
    asyncio.run(main())
