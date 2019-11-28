#!/usr/bin/env python

import os
import sys
from argparse import ArgumentParser

import iterm2
from commitizen.config import read_cfg
from commitizen.commands.commit import Commit


def run_commitizen_questionaire():
    config = read_cfg()
    commit = Commit(config, {})
    answers = commit.prompt_commit_questions()
    return answers


def get_git_message_file():
    return os.path.join(os.getcwd(), ".git", ".gitmessage")


def save_answers(answers):
    git_message_file = get_git_message_file()
    with open(git_message_file, "w") as f:
        f.write(answers)


def run_commitizen():
    answers = run_commitizen_questionaire()
    save_answers(answers)


async def run_in_tab(connection):
    git_work_tree = os.getcwd()
    venv_path = os.path.join(git_work_tree, "venv", "bin", "activate")
    script_path = os.path.join(git_work_tree, "scripts", os.path.basename(sys.argv[0]))
    app = await iterm2.async_get_app(connection)
    new_session = (
        await app.current_terminal_window.current_tab.current_session.async_split_pane()
    )
    await run_commands_in_session(new_session, git_work_tree, venv_path, script_path)
    await wait_for_commands(connection, new_session)
    await new_session.async_send_text("exit\n", suppress_broadcast=True)
    await wait_until_session_closes(connection, new_session)


async def run_commands_in_session(session, git_work_tree, venv_path, script_path):
    await session.async_activate()
    await session.async_send_text("cd " + git_work_tree + "\n", suppress_broadcast=True)
    await session.async_send_text(". " + venv_path + "\n", suppress_broadcast=True)
    await session.async_send_text("clear\n", suppress_broadcast=True)
    await session.async_send_text(script_path + " -n\n", suppress_broadcast=True)


async def wait_for_commands(connection, session):
    job_name = ""
    async with iterm2.VariableMonitor(
        connection, iterm2.VariableScopes.SESSION, "jobName", session.session_id,
    ) as mon:
        while job_name not in ["bash", "zsh"]:
            job_name = await mon.async_get()


async def wait_until_session_closes(connection, session):
    session_id = None
    async with iterm2.SessionTerminationMonitor(connection) as mon:
        while session.session_id != session_id:
            session_id = await mon.async_get()


def run_in_iterm2():
    iterm2.run_until_complete(run_in_tab)


def run(args):
    try:
        run_commitizen() if args.n else run_in_iterm2()
    except Exception as e:
        print(e, file=sys.stderr)
        exit(1)


def main():
    parser = ArgumentParser(
        description="Run commitizen questionaire in iTerm2 so it can be run from a Git hook"
    )
    parser.add_argument("-n", help="do not embed in iTerm2", action="store_true")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
