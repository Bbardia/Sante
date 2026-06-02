import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import {
  Title,
  Button,
  Group,
  Table,
  Modal,
  Stack,
  Text,
  Box,
  Paper,
} from "@mantine/core";
import { listDebts, payDebt, ApiError } from "../api/client";

export default function DebtsPage() {
  const queryClient = useQueryClient();
  const [confirmId, setConfirmId] = useState<number | null>(null);

  const { data: debts = [], isLoading } = useQuery({
    queryKey: ["debts"],
    queryFn: listDebts,
  });

  const payMutation = useMutation({
    mutationFn: (saleId: number) => payDebt(saleId),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      notifications.show({
        color: "green",
        title: "Debt paid",
        message: `Sale #${updated.id} marked as paid.`,
      });
      setConfirmId(null);
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to mark as paid.";
      notifications.show({ color: "red", title: "Error", message: msg });
      setConfirmId(null);
    },
  });

  const totalOutstanding = debts.reduce((sum, d) => sum + d.total, 0);

  const confirmRow = confirmId !== null ? debts.find((d) => d.id === confirmId) : null;

  return (
    <Box>
      <Title order={3} mb="md">Debts</Title>

      {/* Summary */}
      <Group justify="flex-end" mb="xs">
        <Text size="sm" c="dimmed">Total outstanding:</Text>
        <Text fw={600} c="red">{totalOutstanding.toFixed(2)}</Text>
      </Group>

      {/* Table */}
      <Paper withBorder radius="sm">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>Date</Table.Th>
              <Table.Th>Customer</Table.Th>
              <Table.Th>Amount</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading && (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <Text c="dimmed" size="sm">Loading…</Text>
                </Table.Td>
              </Table.Tr>
            )}
            {!isLoading && debts.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <Text c="dimmed" size="sm">No outstanding debts.</Text>
                </Table.Td>
              </Table.Tr>
            )}
            {debts.map((debt) => (
              <Table.Tr key={debt.id}>
                <Table.Td>{debt.id}</Table.Td>
                <Table.Td>{new Date(debt.created_at).toLocaleString()}</Table.Td>
                <Table.Td>{debt.customer_name ?? "—"}</Table.Td>
                <Table.Td>{debt.total.toFixed(2)}</Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    color="green"
                    variant="light"
                    loading={payMutation.isPending && confirmId === debt.id}
                    onClick={() => setConfirmId(debt.id)}
                  >
                    Mark as paid
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {/* Confirm Modal */}
      <Modal
        opened={confirmId !== null}
        onClose={() => setConfirmId(null)}
        title="Confirm payment"
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Mark sale <strong>#{confirmRow?.id}</strong>{" "}
            {confirmRow?.customer_name ? `(${confirmRow.customer_name})` : ""} as paid?
            Amount: <strong>{confirmRow?.total.toFixed(2)}</strong>
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="light" color="gray" onClick={() => setConfirmId(null)}>
              Cancel
            </Button>
            <Button
              color="green"
              loading={payMutation.isPending}
              onClick={() => confirmId !== null && payMutation.mutate(confirmId)}
            >
              Confirm
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Box>
  );
}
