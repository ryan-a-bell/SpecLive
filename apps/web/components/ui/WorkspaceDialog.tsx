"use client";

import { FormEvent, useEffect, useState } from "react";
import { X } from "lucide-react";
import { useCreateWorkspace, useUpdateWorkspace } from "@/lib/hooks";
import { useNavStore } from "@/lib/nav-store";
import { useToast } from "@/lib/toast";
import type { Workspace } from "@/lib/workspaces";

export function WorkspaceDialog({
  open,
  onClose,
  workspace,
}: {
  open: boolean;
  onClose: () => void;
  workspace?: Workspace;
}) {
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [description, setDescription] = useState("");
  const createWorkspace = useCreateWorkspace();
  const updateWorkspace = useUpdateWorkspace();
  const selectWorkspace = useNavStore((state) => state.selectWorkspace);
  const toast = useToast((state) => state.show);
  const editing = Boolean(workspace);

  useEffect(() => {
    if (!open) return;
    setName(workspace?.name ?? "");
    setIndustry(workspace?.industry ?? "");
    setWebsite(workspace?.website ?? "");
    setDescription(workspace?.description ?? "");
  }, [open, workspace]);

  if (!open) return null;

  const pending = createWorkspace.isPending || updateWorkspace.isPending;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (editing && workspace) {
      updateWorkspace.mutate(
        { workspaceId: workspace.id, body: { industry, website, description } },
        {
          onSuccess: () => {
            toast("Client context updated");
            onClose();
          },
          onError: () => toast("Could not update the workspace"),
        },
      );
      return;
    }

    createWorkspace.mutate(
      { name, industry, website, description },
      {
        onSuccess: (created) => {
          selectWorkspace(created.id);
          toast(`Created ${created.name}`);
          onClose();
        },
        onError: (error) =>
          toast(error instanceof Error ? error.message : "Could not create workspace"),
      },
    );
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <div
        className="modal-card workspace-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workspace-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <div className="modal-eyebrow">Workspace profile</div>
            <h2 id="workspace-dialog-title">{editing ? "Edit client context" : "New workspace"}</h2>
          </div>
          <button className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} strokeWidth={2} />
          </button>
        </div>
        <form onSubmit={submit}>
          <label className="field-label">
            Client name
            <input
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Acme Logistics"
              disabled={editing}
              required
            />
          </label>
          <div className="field-grid">
            <label className="field-label">
              Industry
              <input
                value={industry}
                onChange={(event) => setIndustry(event.target.value)}
                placeholder="Logistics"
              />
            </label>
            <label className="field-label">
              Website
              <input
                value={website}
                onChange={(event) => setWebsite(event.target.value)}
                placeholder="https://client.example"
                inputMode="url"
              />
            </label>
          </div>
          <label className="field-label">
            Client context
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What does this client do, and what should the team remember before a discovery call?"
              rows={5}
            />
          </label>
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose} disabled={pending}>
              Cancel
            </button>
            <button type="submit" className="btn primary" disabled={pending || !name.trim()}>
              {pending ? "Saving…" : editing ? "Save context" : "Create workspace"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
