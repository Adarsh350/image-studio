#!/usr/bin/env node
// Stop hook for the maintainer's machine: keeps the image-studio repo pushed after every change.
//
//   Wire it under hooks.Stop in ~/.claude/settings.json:  node "<skill-dir>/scripts/autosync.mjs"
//   node autosync.mjs --self-test
//
// Stage 1 (stop_hook_active false, uncommitted changes): block once and ask Claude to commit them
// atomically with real messages. Stage 2 (stop_hook_active true, still dirty): commit what is left
// itself so the hook can never loop. Either way, commits ahead of origin are pushed to main.
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SKILL_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");

function git(dir, ...args) {
  const r = spawnSync("git", ["-C", dir, ...args], { encoding: "utf8", timeout: 30000 });
  return { ok: r.status === 0, out: (r.stdout || "").trim(), err: (r.stderr || r.error?.message || "").trim() };
}

function push(dir) {
  if (!git(dir, "rev-parse", "--abbrev-ref", "@{u}").ok) return null; // no upstream yet: nothing to push to
  const ahead = Number(git(dir, "rev-list", "--count", "@{u}..HEAD").out || 0);
  if (!ahead) return null;
  if (git(dir, "push", "-q").ok) return `image-studio: pushed ${ahead} commit(s) to origin.`;
  // Rejected (another machine pushed first) or offline: rebase onto origin once, then retry.
  if (!git(dir, "pull", "--rebase", "-q").ok) {
    git(dir, "rebase", "--abort");
    return "image-studio: push failed and the rebase onto origin conflicted. Resolve it in the skill dir and push by hand.";
  }
  return git(dir, "push", "-q").ok
    ? `image-studio: rebased on origin and pushed ${ahead} commit(s).`
    : "image-studio: push failed (offline?). The commits stay local and go out on the next stop.";
}

function sync(dir, stopHookActive) {
  if (!git(dir, "rev-parse", "--git-dir").ok) return {};
  const dirty = git(dir, "status", "--porcelain").out;
  if (dirty && !stopHookActive) {
    return {
      decision: "block",
      reason:
        `The image-studio skill (${dir}) has uncommitted changes:\n${dirty}\n` +
        "It is a repo that auto-pushes to main. Commit the changes now in atomic commits " +
        "(one logical change each; imperative subject of 72 characters or fewer; a body that says why; " +
        "no AI attribution trailers), using git -C on that directory. Don't push: this hook pushes.",
    };
  }
  if (dirty) {
    const files = dirty.split("\n").map((l) => l.slice(3)).join(", ");
    git(dir, "add", "-A");
    const c = git(dir, "commit", "-q", "-m", "Sync remaining image-studio edits",
      "-m", `Left uncommitted at the end of a session, so the Stop hook committed them so the GitHub copy stays current: ${files}`);
    if (!c.ok) return { systemMessage: `image-studio: auto-commit failed: ${c.err}` };
  }
  const msg = push(dir);
  return msg ? { systemMessage: msg } : {};
}

function selfTest() {
  const ok = (c, m) => { if (!c) throw new Error(`self-test: ${m}`); };
  const tmp = mkdtempSync(join(tmpdir(), "autosync-"));
  try {
    const bare = join(tmp, "origin.git"), work = join(tmp, "work");
    spawnSync("git", ["init", "-q", "--bare", "-b", "main", bare]);
    spawnSync("git", ["clone", "-q", bare, work]);
    for (const [k, v] of [["user.name", "t"], ["user.email", "t@t"], ["commit.gpgsign", "false"]]) git(work, "config", k, v);
    writeFileSync(join(work, "a.md"), "one\n");
    git(work, "add", "-A"); git(work, "commit", "-q", "-m", "Initial"); git(work, "push", "-q", "-u", "origin", "main");

    ok(JSON.stringify(sync(work, false)) === "{}", "clean tree is a no-op");
    writeFileSync(join(work, "a.md"), "two\n");
    const r1 = sync(work, false);
    ok(r1.decision === "block" && r1.reason.includes("a.md"), "dirty tree blocks first");
    const r2 = sync(work, true);
    ok(!git(work, "status", "--porcelain").out, "second stop commits the rest");
    ok(r2.systemMessage?.includes("pushed 1"), "and pushes it");
    ok(git(bare, "log", "-1", "--format=%s", "main").out === "Sync remaining image-studio edits", "origin has the commit");
    ok(!git(bare, "log", "-1", "--format=%B", "main").out.includes("Co-Authored"), "no attribution trailer");
    ok(JSON.stringify(sync(join(tmp), false)) === "{}", "non-repo dir is a no-op");
    console.log("autosync self-test ok");
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

if (process.argv[2] === "--self-test") selfTest();
else {
  let input = "";
  process.stdin.on("data", (d) => (input += d));
  process.stdin.on("end", () => {
    let active = false;
    try { active = !!JSON.parse(input || "{}").stop_hook_active; } catch {}
    const out = sync(SKILL_DIR, active);
    if (Object.keys(out).length) process.stdout.write(JSON.stringify(out));
  });
}
