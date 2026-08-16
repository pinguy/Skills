---
name: privileged-operations
description: Safely perform Linux tasks that may require root privileges. Use whenever an install, system configuration change, protected file edit, service operation, package transaction, permission change, mount, device operation, or other command may need elevation. Keep work unprivileged by default; when root is genuinely required, elevate only the smallest necessary command with pkexec so the user can authenticate interactively. Never silently fall back to sudo, su, a root shell, password piping, or broad root execution.
---

# Privileged Operations

Safely handle Linux work that may cross the root privilege boundary.

The core rule is:

> **Do everything possible as the normal user. If one specific operation genuinely requires root, run only that operation through `pkexec` so the user can approve it interactively.**

This is not merely "replace `sudo` with `pkexec`." Keep the privileged surface small, explicit, understandable, and reversible.

The default workflow is:

```text
inspect as user
→ diagnose as user
→ download/build/generate as user
→ validate as user
→ identify the exact privileged step
→ explain what it changes
→ run that step with pkexec
→ verify as user
```

Do not become root first and then perform the task.

---

## Decide whether root is actually required

Before elevating, be able to complete this sentence:

> "This exact command needs root because ________, and the rest of the task does not."

If the reason is unclear, investigate first.

Operations that normally stay unprivileged include:

- editing files in `$HOME`
- cloning, extracting, compiling, testing, and generating files
- `make`, `cmake`, `meson`, `ninja`, `cargo`, Python, and Node project tooling
- `systemctl --user ...`
- `makepkg`, `yay`, and `paru`

Root may legitimately be needed for:

- system package transactions
- protected writes under `/etc`, `/usr`, `/opt`, `/boot`, and similar paths
- system-level services
- system-owned permissions or ownership
- firewall, mount, kernel, boot, or device configuration
- the final install step of a completed build into a protected prefix

Even then, elevate only the protected operation.

**Good:**

```sh
make
pkexec /usr/bin/make install
```

**Bad:**

```sh
pkexec /bin/bash
make
make install
```

The bad version unnecessarily gives the entire build root access and can leave root-owned files in the user's work tree.

---

## Use pkexec for elevation

When root is required, use:

```sh
pkexec <program> <arguments...>
```

Prefer invoking the real executable directly.

**Prefer:**

```sh
pkexec /usr/bin/install -Dm644 ./example.conf /etc/example/example.conf
```

**Avoid:**

```sh
pkexec sh -c 'cp ./example.conf /etc/example/example.conf'
```

A privileged shell increases quoting risk and can execute more than intended. Use `sh -c` only when shell syntax is genuinely necessary and no clean direct-command form exists.

Before depending on elevation, check:

```sh
command -v pkexec
```

If `pkexec` is missing or cannot authenticate, report the blocker. Do not silently substitute `sudo`, `su`, `doas`, a root shell, or another mechanism.

If package installation is needed to obtain `pkexec`, identify the distribution before naming the package that provides it.

---

## Authentication belongs to the user

Let polkit and the user's authentication agent handle credentials.

Never:

- ask the user to send their password
- store, log, echo, or pipe a password
- put a password in a command or temporary file
- use `sudo -S`
- automate password entry
- create passwordless privilege rules merely to avoid prompts

If the user cancels or denies the authentication prompt, stop that privileged operation. Do not spam retries or treat an earlier authentication as blanket approval for unrelated later changes.

If `pkexec` fails because no polkit authentication agent is available, report the actual error and likely agent/session problem. Do not fall back to `sudo`.

---

## Keep the privileged boundary narrow

Prefer a small, understandable root operation over a privileged command chain.

Avoid:

```sh
pkexec sh -c 'command1 && command2 && command3 && command4'
```

when only part of the chain needs root.

Do not start a persistent root shell by default:

```sh
pkexec bash
pkexec zsh
pkexec fish
pkexec sh
```

Treat an interactive root shell as exceptional and use it only when the user explicitly needs that mode and the task cannot reasonably be reduced to narrow commands.

The goal is not the fewest prompts. The goal is the smallest understandable privilege boundary.

---

## Resolve paths and environment before elevation

`pkexec` intentionally uses a restricted environment. Do not assume it preserves `PATH`, aliases, shell functions, virtual environments, custom library paths, project variables, `HOME`, or desktop/session variables.

Resolve important paths before elevation and pass explicit arguments.

For sensitive commands, prefer known absolute executable paths where practical:

```sh
command -v systemctl
pkexec /usr/bin/systemctl restart example.service
```

Quote paths and variables:

```sh
pkexec /usr/bin/install -Dm644 "$src" "$dest"
```

Where supported, use `--` before path operands that might begin with `-`:

```sh
pkexec /usr/bin/rm -- "$file"
```

Do not trust a project-local executable merely because its name resembles a system program.

---

## Build and generate as the normal user

Keep compilation, downloads, code generation, project scripts, and testing unprivileged.

Preferred pattern:

```text
build as user → test as user → validate → pkexec final install → verify as user
```

This avoids root-owned build artifacts, poisoned user caches, and arbitrary build scripts running with full system access.

If a privileged operation unexpectedly creates root-owned files inside a user work tree, identify the exact affected paths and repair only those paths.

Never use a broad repair such as:

```sh
pkexec chown -R "$USER:$USER" "$HOME"
```

That can damage files intentionally owned by root or another user.

---

## Arch, makepkg, yay, and paru

Never run `makepkg`, `yay`, or `paru` as root.

Do not do this:

```sh
pkexec yay -S package
pkexec paru -S package
pkexec makepkg -si
```

If the workflow must preserve a strict `pkexec`-only elevation boundary, split the stages:

1. inspect the `PKGBUILD` as the normal user
2. install required system dependencies explicitly with `pkexec pacman` where necessary
3. build with `makepkg` as the normal user
4. install the resulting package with `pkexec pacman -U`
5. verify the installed package

Example:

```sh
makepkg
pkexec /usr/bin/pacman -U ./package-name-*.pkg.tar.zst
pacman -Q package-name
```

Do not use root to bypass `makepkg` refusing to build as root.

---

## System package managers

A system package transaction that genuinely needs root may be wrapped directly with `pkexec`.

On Arch:

```sh
pkexec /usr/bin/pacman -S --needed package-name
```

Before broad installs, upgrades, or removals, inspect the proposed transaction.

Do not add non-interactive flags such as `--noconfirm` by default to potentially destructive package operations. Dependency, conflict, and removal prompts are useful safety boundaries.

---

## Systemd

Determine whether a unit is user-level or system-level before elevating.

```sh
# user unit
systemctl --user restart example.service

# system unit
pkexec /usr/bin/systemctl restart example.service
```

Do not elevate user services unnecessarily.

After changing a system unit, reload only when needed:

```sh
pkexec /usr/bin/systemctl daemon-reload
```

Then perform the exact intended action: start, stop, restart, reload, enable, disable, mask, or unmask. These are not interchangeable.

Verify afterwards:

```sh
systemctl status example.service
journalctl -u example.service -n 50 --no-pager
```

If journal access itself requires root, elevate only that read operation.

---

## Edit protected files through a staged replacement

Avoid launching a full editor as root.

Use this pattern:

1. read the existing file unprivileged where possible
2. create a user-owned working copy or temporary replacement
3. edit and validate it as the normal user
4. inspect the diff
5. create a backup or rollback point when warranted
6. install the final file with one narrow `pkexec` command
7. validate the installed result

Example:

```sh
cp /etc/example.conf ./example.conf.new
# edit and validate ./example.conf.new

diff -u /etc/example.conf ./example.conf.new
pkexec /usr/bin/cp -a /etc/example.conf /etc/example.conf.bak
pkexec /usr/bin/install -m 644 ./example.conf.new /etc/example.conf
```

Adapt ownership, permissions, ACLs, extended attributes, security labels, and other metadata to the actual target. `0644` is not universally correct.

Before overwriting a protected target, determine whether it is a file, directory, symlink, mount point, generated file, or package-owned file.

Useful checks include:

```sh
ls -ld -- "$target"
readlink -f -- "$target"
```

Prefer supported overrides, drop-ins, `/etc` configuration, or `/usr/local` installation over directly editing package-owned vendor files under `/usr`.

---

## Protected redirection

The user's shell performs redirection before `pkexec` starts, so this does not elevate the `>` write:

```sh
pkexec echo "value" > /etc/example.conf
```

For a short stream, narrowly scoped `tee` may be appropriate:

```sh
printf '%s\n' "value" | pkexec /usr/bin/tee /etc/example.conf >/dev/null
```

For non-trivial files, generate and validate the file as the normal user, then install it with `pkexec`.

---

## Downloads and third-party installers

Do not download changing remote content directly into protected system paths as root.

Prefer:

```text
download as user → verify → inspect/extract/build as user → elevate final install only
```

Avoid:

```sh
curl ... | pkexec sh
```

If upstream documentation says the whole installer must run as root:

1. inspect the installer first
2. determine which parts actually need root
3. prefer a documented staged or non-root route where available
4. never pipe a remote script directly into a privileged shell
5. treat unavoidable full-root execution as materially higher risk

`pkexec` does not make an opaque third-party root installer safe merely by launching it interactively.

---

## Validate, back up, and define rollback

Do as much validation as possible before elevation: syntax checks, diffs, unit verification, package state, hashes/signatures where applicable, free space, binary tests, destination checks, and device/mount checks.

For configuration changes, prefer:

```text
generate → diff → validate → backup → pkexec install → validate again
```

For risky changes, know the rollback path before applying them.

Avoid repeatedly overwriting the same backup when history matters. Use a unique backup name where appropriate:

```sh
stamp="$(date +%Y%m%d-%H%M%S)"
pkexec /usr/bin/cp -a /etc/example.conf "/etc/example.conf.bak-$stamp"
```

If rollback is difficult or impossible, say so before making the change.

---

## Destructive operations need stronger checks

Treat privileged destructive commands as high risk, especially:

- `rm -rf`, recursive `chmod`, or recursive `chown`
- `dd`, `mkfs.*`, `fdisk`, `sfdisk`, `parted`, or `wipefs`
- mounts and unmounts
- broad package removals
- `systemctl disable` or `mask`
- `iptables` or `nft`
- bootloader, initramfs, `/boot`, or EFI operations
- kernel parameters and block-device changes

Before running them:

- identify the exact target
- resolve variables before elevation
- reject empty or suspicious path values
- inspect symlinks where relevant
- verify device/mount state
- understand what will be removed or overwritten
- establish rollback or backup where practical

Never construct a privileged recursive deletion from an unchecked variable.

Before something conceptually like:

```sh
pkexec /usr/bin/rm -rf -- "$target"
```

verify that `$target` is non-empty, resolves to the intended location, and cannot collapse to `/`, `$HOME`, or an unexpectedly broad parent.

Prefer package-manager or purpose-built removal commands over recursive deletion where available.

---

## Devices, partitions, and mounts

For destructive device work:

1. identify the device as the normal user
2. verify stable identity where possible instead of trusting only `/dev/sdX`
3. check whether it is mounted or in use
4. show the exact target before changing it
5. elevate only the final protected operation

Never guess between ambiguous destructive targets. If the target cannot be established confidently, stop rather than choosing one.

---

## Do not weaken security to avoid prompts

Never solve privilege friction by permanently making the system less secure.

Do not:

- make protected files world-writable
- give broad system directories to the user
- add blanket passwordless polkit or sudo rules
- disable polkit or authentication
- set unsafe setuid bits
- grant broad Linux capabilities when a narrower solution exists
- run long-lived services as root unnecessarily

A one-time authentication prompt is preferable to a permanent privilege hole.

---

## Failure handling

Authentication success does not prove the command succeeded.

After every privileged change, inspect the exit status and verify the resulting state.

Examples:

```sh
test -f /etc/example.conf
pacman -Q package-name
systemctl status example.service
ls -l /usr/local/bin/example
```

If a privileged operation fails:

1. stop
2. inspect the actual error
3. determine whether anything changed before the failure
4. do not blindly rerun the same command
5. roll back if a broken intermediate state was created and rollback is appropriate
6. report what succeeded, what failed, and what remains uncertain

Do not stack more privileged changes on top of an unknown partial state.

Prefer idempotent commands where practical, and check before appending settings that could duplicate on rerun.

---

## Reporting

After privileged work, tell the user concisely:

- what required root and why
- which `pkexec` command or commands were run
- whether they succeeded
- what changed
- how the result was verified
- any backup or rollback path that remains relevant
- anything still unverified

Do not expose credentials or authentication data.

For routine successful work, keep this short. For risky, destructive, or partially failed work, give enough detail to make the resulting system state clear.

---

## Hard constraints

Keep these invariant throughout the task:

1. Use normal user privileges by default.
2. Use `pkexec` when a specific command genuinely requires root.
3. Never silently fall back to `sudo`, `su`, `doas`, or another elevation mechanism.
4. Never request, capture, store, pipe, or automate the user's password.
5. Do not run an entire build, project, editor, helper, or shell as root when a narrow privileged command will do.
6. Never run `makepkg`, `yay`, or `paru` as root.
7. Keep user-owned work trees and caches user-owned.
8. Validate before elevation and verify after elevation.
9. Back up or define rollback before risky system changes where practical.
10. Treat authentication cancellation as refusal to perform that privileged operation.
11. Do not weaken persistent system security merely to avoid authentication prompts.
12. Stop and inspect partial failure rather than stacking more privileged changes on top of an unknown state.
