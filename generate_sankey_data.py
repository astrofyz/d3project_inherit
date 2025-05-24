import json
import os
from collections import defaultdict

def read_tournament_years(mapping_file):
    """Read tournament ID to year mapping from file"""
    tournament_years = {}
    with open(mapping_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Assuming format: tournament_id:year
            parts = line.strip().split(':')
            if len(parts) == 2:
                tournament_id, year = parts
                tournament_years[tournament_id] = year
    return tournament_years

def get_full_player_name(player):
    """Combine player's name, patronymic, and surname"""
    parts = [player['surname'], player['name']]
    if player.get('patronymic'):
        parts.append(player['patronymic'])
    return ' '.join(parts)

def read_tournament_files(directory, mapping_file):
    """
    Read all tournament files from the directory and organize data by year
    Returns a dictionary with years as keys and team data as values
    """
    teams_data = defaultdict(dict)
    
    # Read tournament-year mapping
    tournament_years = read_tournament_years(mapping_file)
    # print("Tournament years mapping:", tournament_years)  # Debug print
    
    # Get all tournament files
    files = [f for f in os.listdir(directory) if f.endswith('.json')]
    # print("Found files:", files)  # Debug print
    
    # Sort files by year (most recent first)
    def get_year_from_filename(filename):
        tournament_id = filename.split('_')[-1].replace('.json', '')
        # print("test sorting files")
        # print(tournament_id, tournament_years.get(tournament_id, 0))
        return int(tournament_years.get(tournament_id, 0))  # Use 0 as fallback for unknown tournaments
    
    files.sort(key=get_year_from_filename, reverse=True)  # Sort by year, most recent first
    # print("Sorted files:", files)  # Debug print
    
    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            tournament_data = json.load(f)
            
            # Extract tournament ID from filename
            tournament_id = filename.split('_')[-1].replace('.json', '')
            
            # Get year from mapping, or use tournament ID if not found
            year = str(tournament_years.get(tournament_id, tournament_id))
            # print(f"Processing tournament {tournament_id} (year {year})")  # Debug print
            
            # Process each team in the tournament
            for team_entry in tournament_data:
                team = team_entry['team']
                team_name = team['name']
                
                # Get player names
                players = []
                for member in team_entry['teamMembers']:
                    player = member['player']
                    full_name = get_full_player_name(player)
                    players.append(full_name)
                
                # Store team data
                teams_data[year][team_name] = players
    
    # print("Processed tournaments:", sorted(teams_data.keys()))  # Debug print
    return teams_data

def create_sankey_data(teams_data):
    """
    Create Sankey diagram data structure from teams data
    
    teams_data format:
    {
        "2024": {
            "Team1": ["Player1", "Player2", ...],
            "Team2": ["Player1", "Player3", ...],
            ...
        },
        "2023": {
            ...
        },
        ...
    }
    """
    nodes = []
    links = []
    node_id = 0
    year_to_nodes = defaultdict(list)
    
    # First pass: count teams per year and find max
    teams_per_year = {year: len(teams) for year, teams in teams_data.items()}
    max_teams = max(teams_per_year.values())
    print("Teams per year:", teams_per_year)
    print("Max teams:", max_teams)
    
    # Create nodes for each team in each year
    for year in sorted(teams_data.keys(), reverse=True):  # Process years in reverse order (newest first)
        # print(f"Processing year {year}")
        teams = teams_data[year]
        current_teams = len(teams)
        
        # Add real teams
        for team_name, players in teams.items():
            node = {
                "name": f"{year}_{team_name}",  # Unique identifier
                "real_name": team_name,
                "team": "\n".join(players),  # Players as newline-separated string
                "year": year,
                "node": node_id,
                "color": node_id % max_teams  # Using max_teams as modulo to reset colors each year
            }
            nodes.append(node)
            year_to_nodes[year].append(node_id)
            node_id += 1
        
        # Add dummy teams if needed
        dummy_nodes_needed = max_teams - current_teams
        for i in range(dummy_nodes_needed):
            dummy_name = f"Команда {i+1}"  # Using Russian "Команда" (Team) for dummy names
            dummy_node = {
                "name": f"000000",  # Unique identifier for dummy
                "real_name": dummy_name,  # Using a proper team name instead of "000000"
                "team": "",  # Empty team
                "year": year,
                "node": node_id,
                "color": node_id % max_teams  # Using max_teams as modulo to reset colors each year
            }
            nodes.append(dummy_node)
            year_to_nodes[year].append(node_id)
            node_id += 1
    
    # Create links between teams that share players
    sorted_years = sorted(teams_data.keys(), reverse=True)  # Sort years in reverse order
    for year_idx, year in enumerate(sorted_years):
        if year_idx == 0:
            continue
            
        prev_year = sorted_years[year_idx - 1]
        
        # Compare teams between consecutive years
        for prev_team_id in year_to_nodes[prev_year]:
            for curr_team_id in year_to_nodes[year]:
                prev_team = nodes[prev_team_id]
                curr_team = nodes[curr_team_id]
                
                # Skip if either team is a dummy (has empty team list)
                if not prev_team["team"] or not curr_team["team"]:
                    continue
                
                # Get sets of players
                prev_players = set(prev_team["team"].split("\n"))
                curr_players = set(curr_team["team"].split("\n"))
                
                # Calculate shared players
                shared_players = prev_players.intersection(curr_players)
                
                if shared_players:
                    link = {
                        "source": prev_team_id,
                        "target": curr_team_id,
                        "value": len(shared_players),
                        "team": "\n".join(shared_players)
                    }
                    links.append(link)
    
    # Add dummy links to maintain grid structure
    for year_idx in range(len(sorted_years) - 1):
        current_year = sorted_years[year_idx]
        next_year = sorted_years[year_idx + 1]
        
        # For each position in the grid
        for pos in range(max_teams):
            source_id = year_to_nodes[current_year][pos]
            target_id = year_to_nodes[next_year][pos]
            
            # Add dummy link with small value
            dummy_link = {
                "source": source_id,
                "target": target_id,
                "value": 0.5,  # Small value for visual connection
                "team": ""  # Empty team list for dummy link
            }
            links.append(dummy_link)
    
    return {"nodes": nodes, "links": links}

def save_sankey_data(data, max_teams, output_file="all_teams.json"):
    """Save the Sankey data to a JSON file"""
    output_data = {
        "nodes": data["nodes"],
        "links": data["links"],
        "max_teams": max_teams
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # Directory containing tournament files
    tournament_dir = "studchr_jsons/json"  # Change this to your directory path
    mapping_file = "studchr_jsons/studchr_ids.txt"  # Path to tournament-year mapping file
    
    # Read and process tournament files
    teams_data = read_tournament_files(tournament_dir, mapping_file)
    
    # Generate Sankey data
    sankey_data = create_sankey_data(teams_data)
    
    # Get max teams per year
    teams_per_year = {year: len(teams) for year, teams in teams_data.items()}
    max_teams = max(teams_per_year.values())
    
    # Save the result
    save_sankey_data(sankey_data, max_teams, "all_teams_2025.json") 