import os
import requests

BASE_URL = "https://api.clickup.com/api/v2"


def _headers():
    return {"Authorization": os.environ["CLICKUP_API_KEY"]}


def get_workspaces() -> dict:
    """Lists all ClickUp workspaces (teams) the user belongs to.

    Returns workspace names and IDs so the user can navigate their task hierarchy.
    """
    try:
        resp = requests.get(f"{BASE_URL}/team", headers=_headers(), timeout=15)
        resp.raise_for_status()
        teams = resp.json().get("teams", [])
        return {
            "status": "success",
            "workspaces": [
                {"id": t["id"], "name": t["name"]}
                for t in teams
            ],
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def get_spaces(team_id: str) -> dict:
    """Lists all spaces in a ClickUp workspace.

    Args:
        team_id: The workspace (team) ID to list spaces for.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/team/{team_id}/space",
            headers=_headers(),
            params={"archived": "false"},
            timeout=15,
        )
        resp.raise_for_status()
        spaces = resp.json().get("spaces", [])
        return {
            "status": "success",
            "spaces": [
                {"id": s["id"], "name": s["name"]}
                for s in spaces
            ],
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def get_lists(space_id: str) -> dict:
    """Lists all task lists in a ClickUp space, including lists inside folders and folderless lists.

    Args:
        space_id: The space ID to list task lists for.
    """
    try:
        all_lists = []

        # Get folders and their lists
        resp = requests.get(
            f"{BASE_URL}/space/{space_id}/folder",
            headers=_headers(),
            params={"archived": "false"},
            timeout=15,
        )
        resp.raise_for_status()
        for folder in resp.json().get("folders", []):
            for lst in folder.get("lists", []):
                all_lists.append({
                    "id": lst["id"],
                    "name": lst["name"],
                    "folder": folder["name"],
                })

        # Get folderless lists
        resp = requests.get(
            f"{BASE_URL}/space/{space_id}/list",
            headers=_headers(),
            params={"archived": "false"},
            timeout=15,
        )
        resp.raise_for_status()
        for lst in resp.json().get("lists", []):
            all_lists.append({
                "id": lst["id"],
                "name": lst["name"],
                "folder": None,
            })

        return {"status": "success", "lists": all_lists}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def get_tasks(list_id: str, status: str = "") -> dict:
    """Gets tasks from a ClickUp list.

    Args:
        list_id: The list ID to fetch tasks from.
        status: Optional status filter like 'open', 'in progress', 'closed'. Leave empty for all tasks.
    """
    try:
        params = {}
        if status:
            params["statuses[]"] = status

        resp = requests.get(
            f"{BASE_URL}/list/{list_id}/task",
            headers=_headers(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        tasks = resp.json().get("tasks", [])
        return {
            "status": "success",
            "tasks": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "status": t["status"]["status"],
                    "priority": t.get("priority", {}).get("priority", "none") if t.get("priority") else "none",
                    "due_date": t.get("due_date"),
                    "assignees": [a["username"] for a in t.get("assignees", [])],
                    "url": t.get("url", ""),
                }
                for t in tasks
            ],
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def get_task_details(task_id: str) -> dict:
    """Gets full details of a specific ClickUp task.

    Args:
        task_id: The task ID to get details for.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/task/{task_id}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        t = resp.json()
        return {
            "status": "success",
            "task": {
                "id": t["id"],
                "name": t["name"],
                "description": t.get("text_content", ""),
                "status": t["status"]["status"],
                "priority": t.get("priority", {}).get("priority", "none") if t.get("priority") else "none",
                "due_date": t.get("due_date"),
                "assignees": [a["username"] for a in t.get("assignees", [])],
                "tags": [tag["name"] for tag in t.get("tags", [])],
                "date_created": t.get("date_created"),
                "date_updated": t.get("date_updated"),
                "url": t.get("url", ""),
            },
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def create_task(list_id: str, name: str, description: str = "", priority: int = 3) -> dict:
    """Creates a new task in a ClickUp list.

    Args:
        list_id: The list ID to create the task in.
        name: The name/title of the new task.
        description: Optional description for the task.
        priority: Priority level: 1=Urgent, 2=High, 3=Normal, 4=Low. Defaults to 3 (Normal).
    """
    try:
        payload = {
            "name": name,
            "description": description,
            "priority": priority,
        }
        resp = requests.post(
            f"{BASE_URL}/list/{list_id}/task",
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        t = resp.json()
        return {
            "status": "success",
            "task_id": t["id"],
            "name": t["name"],
            "url": t.get("url", ""),
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def update_task(task_id: str, status: str = "", priority: int = 0) -> dict:
    """Updates a ClickUp task's status or priority.

    Args:
        task_id: The task ID to update.
        status: New status for the task (e.g., 'open', 'in progress', 'closed'). Leave empty to keep current.
        priority: New priority: 1=Urgent, 2=High, 3=Normal, 4=Low. Use 0 to keep current.
    """
    try:
        payload = {}
        if status:
            payload["status"] = status
        if priority > 0:
            payload["priority"] = priority

        if not payload:
            return {"status": "error", "error_message": "No updates specified. Provide a status or priority."}

        resp = requests.put(
            f"{BASE_URL}/task/{task_id}",
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        t = resp.json()
        return {
            "status": "success",
            "task_id": t["id"],
            "name": t["name"],
            "new_status": t["status"]["status"],
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def add_comment(task_id: str, comment_text: str) -> dict:
    """Adds a comment to a ClickUp task.

    Args:
        task_id: The task ID to add a comment to.
        comment_text: The text of the comment to add.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/task/{task_id}/comment",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"comment_text": comment_text},
            timeout=15,
        )
        resp.raise_for_status()
        return {"status": "success", "message": "Comment added successfully."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}


def close_task(task_id: str) -> dict:
    """Closes/completes a ClickUp task by setting its status to 'closed'.

    Args:
        task_id: The task ID to close.
    """
    try:
        resp = requests.put(
            f"{BASE_URL}/task/{task_id}",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"status": "closed"},
            timeout=15,
        )
        resp.raise_for_status()
        t = resp.json()
        return {
            "status": "success",
            "task_id": t["id"],
            "name": t["name"],
            "new_status": t["status"]["status"],
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_message": str(e)}
