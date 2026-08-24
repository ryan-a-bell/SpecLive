"use client";

import { useId, useState, type FormEvent } from "react";
import { useDeleteSession } from "@/lib/hooks";
import { useNavStore } from "@/lib/nav-store";
import { useToast } from "@/lib/toast";
import type { WorkspaceSession } from "@/lib/workspaces";

export function DeleteConversationButton({
  session,
  className = "btn danger",
  label = "Delete conversation",
}: {
  session: WorkspaceSession;
  className?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);
  const [confirmation, setConfirmation] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const deletion = useDeleteSession();
  const toast = useToast((state) => state.show);
  const titleId = useId();
  const confirmed = confirmation.trim().toUpperCase() === "DELETE";

  function resetAndClose() {
    setOpen(false);
    setStep(1);
    setConfirmation("");
    setDeleteError("");
  }

  function close() {
    if (!deletion.isPending) resetAndClose();
  }

  function permanentlyDelete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmed || deletion.isPending) return;
    setDeleteError("");
    deletion.mutate(session.id, {
      onSuccess: () => {
        const nav = useNavStore.getState();
        if (nav.activeSessionId === session.id) {
          useNavStore.setState({ activeSessionId: null, view: "overview" });
        }
        toast(`Deleted ${session.title}`);
        resetAndClose();
      },
      onError: (error) => {
        const message = error instanceof Error ? error.message : "The server rejected the request.";
        setDeleteError(message);
        toast("Could not delete the conversation");
      },
    });
  }

  return (
    <>
      <button
        type="button"
        className={className}
        onClick={(event) => {
          event.stopPropagation();
          setOpen(true);
        }}
      >
        {label}
      </button>
      {open && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={close}
          onClick={(event) => event.stopPropagation()}
        >
          <div
            className="modal-card danger-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="danger-mark">!</div>
            {step === 1 ? (
              <>
                <h2 id={titleId}>Delete this conversation?</h2>
                <p>
                  <strong>{session.title}</strong> and all of its transcript, requirements,
                  evidence, and branches will be removed.
                </p>
                <div className="modal-actions">
                  <button type="button" className="btn" onClick={close}>
                    Cancel
                  </button>
                  <button type="button" className="btn danger" onClick={() => setStep(2)}>
                    Continue
                  </button>
                </div>
              </>
            ) : (
              <form onSubmit={permanentlyDelete}>
                <h2 id={titleId}>Permanently delete?</h2>
                <p>
                  This cannot be undone. Type <strong>DELETE</strong> to confirm a second time.
                </p>
                <label className="field-label">
                  Confirmation
                  <input
                    autoFocus
                    value={confirmation}
                    onChange={(event) => setConfirmation(event.target.value)}
                    placeholder="DELETE"
                    autoComplete="off"
                  />
                </label>
                {deleteError ? (
                  <p className="form-error" role="alert">
                    Delete failed: {deleteError}
                  </p>
                ) : null}
                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn"
                    onClick={() => {
                      setDeleteError("");
                      setStep(1);
                    }}
                    disabled={deletion.isPending}
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    className="btn danger solid"
                    disabled={!confirmed || deletion.isPending}
                  >
                    {deletion.isPending ? "Deleting…" : "Delete permanently"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
