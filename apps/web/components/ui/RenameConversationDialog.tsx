"use client";

import { useId, useState, type FormEvent } from "react";
import { X } from "lucide-react";
import { useUpdateSession } from "@/lib/hooks";
import { useToast } from "@/lib/toast";
import type { WorkspaceSession } from "@/lib/workspaces";

export function RenameConversationButton({
  session,
  className = "btn",
  label = "Rename",
}: {
  session: WorkspaceSession;
  className?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(session.title);
  const [renameError, setRenameError] = useState("");
  const update = useUpdateSession(session.id);
  const toast = useToast((state) => state.show);
  const titleId = useId();
  const cleanTitle = title.trim();

  function close() {
    if (update.isPending) return;
    setOpen(false);
    setTitle(session.title);
    setRenameError("");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cleanTitle || update.isPending) return;
    setRenameError("");
    update.mutate(
      { title: cleanTitle },
      {
        onSuccess: () => {
          toast("Conversation renamed");
          setOpen(false);
          setRenameError("");
        },
        onError: (error) => {
          setRenameError(error instanceof Error ? error.message : "The server rejected the name.");
        },
      },
    );
  }

  return (
    <>
      <button
        type="button"
        className={className}
        onClick={(event) => {
          event.stopPropagation();
          setTitle(session.title);
          setRenameError("");
          setOpen(true);
        }}
      >
        {label}
      </button>
      {open ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={close}
          onClick={(event) => event.stopPropagation()}
        >
          <form
            className="modal-card rename-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onSubmit={submit}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-head">
              <div>
                <div className="modal-eyebrow">Conversation</div>
                <h2 id={titleId}>Rename conversation</h2>
              </div>
              <button type="button" className="modal-close" onClick={close} aria-label="Close">
                <X size={18} strokeWidth={2} />
              </button>
            </div>
            <label className="field-label">
              Title
              <input
                autoFocus
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={255}
              />
            </label>
            {renameError ? (
              <p className="form-error" role="alert">
                Rename failed: {renameError}
              </p>
            ) : null}
            <div className="modal-actions">
              <button type="button" className="btn" onClick={close} disabled={update.isPending}>
                Cancel
              </button>
              <button
                type="submit"
                className="btn primary"
                disabled={!cleanTitle || update.isPending}
              >
                {update.isPending ? "Saving…" : "Save name"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </>
  );
}
