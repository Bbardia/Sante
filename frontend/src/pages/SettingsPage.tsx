import { useRef, useState } from "react";
import { notifications } from "@mantine/notifications";
import {
  Title,
  Box,
  Stack,
  Button,
  Text,
  Group,
  Paper,
} from "@mantine/core";
import { downloadBackup, restoreDatabase, ApiError } from "../api/client";

export default function SettingsPage() {
  const [backupLoading, setBackupLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleDownloadBackup() {
    setBackupLoading(true);
    try {
      const blob = await downloadBackup();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sante-backup.db";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      notifications.show({
        color: "green",
        title: "Backup downloaded",
        message: "sante-backup.db has been saved.",
      });
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to download backup.";
      notifications.show({ color: "red", title: "Backup failed", message: msg });
    } finally {
      setBackupLoading(false);
    }
  }

  async function handleRestore() {
    if (!restoreFile) return;
    const confirmed = window.confirm(
      "WARNING: This will overwrite ALL current data with the contents of the selected backup file.\n\n" +
        "A safety backup of your current data will be taken automatically before restoring.\n\n" +
        "Are you sure you want to continue?"
    );
    if (!confirmed) return;

    setRestoreLoading(true);
    try {
      const result = await restoreDatabase(restoreFile);
      const safetyMsg = result.safety_backup
        ? ` A safety backup was saved as: ${result.safety_backup}`
        : "";
      notifications.show({
        color: "green",
        title: "Restore complete",
        message: `Database restored successfully.${safetyMsg} The app will now reload.`,
        autoClose: 5000,
      });
      setTimeout(() => window.location.reload(), 2000);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to restore database.";
      notifications.show({ color: "red", title: "Restore failed", message: msg });
    } finally {
      setRestoreLoading(false);
    }
  }

  return (
    <Box>
      <Title order={3} mb="md">
        Settings
      </Title>

      <Stack gap="md" maw={480}>
        {/* Backup card */}
        <Paper withBorder p="md" radius="sm">
          <Title order={5} mb="xs">
            Backup
          </Title>
          <Text size="sm" c="dimmed" mb="sm">
            Download a full copy of the database as a .db file.
          </Text>
          <Button
            loading={backupLoading}
            onClick={handleDownloadBackup}
          >
            Download backup
          </Button>
        </Paper>

        {/* Restore card */}
        <Paper withBorder p="md" radius="sm">
          <Title order={5} mb="xs">
            Restore
          </Title>
          <Text size="sm" c="dimmed" mb="sm">
            Restore the database from a previously downloaded .db backup file.
            A safety backup of the current data will be taken automatically before
            overwriting.
          </Text>
          <Stack gap="sm">
            <input
              ref={fileInputRef}
              type="file"
              accept=".db"
              style={{ display: "none" }}
              onChange={(e) => setRestoreFile(e.currentTarget.files?.[0] ?? null)}
            />
            <Group gap="sm" align="center">
              <Button
                variant="light"
                onClick={() => fileInputRef.current?.click()}
              >
                Choose file
              </Button>
              <Text size="sm" c={restoreFile ? undefined : "dimmed"}>
                {restoreFile ? restoreFile.name : "No file chosen"}
              </Text>
            </Group>
            <Button
              color="orange"
              disabled={!restoreFile}
              loading={restoreLoading}
              onClick={handleRestore}
            >
              Restore
            </Button>
          </Stack>
        </Paper>
      </Stack>
    </Box>
  );
}
