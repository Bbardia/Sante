import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  Title,
  TextInput,
  NumberInput,
  Button,
  Group,
  Table,
  Modal,
  Stack,
  ActionIcon,
  Badge,
  Text,
  Box,
} from "@mantine/core";
import {
  listInventory,
  addStock,
  updateInventory,
  deleteInventory,
  resetInventory,
  ApiError,
  type Inventory,
} from "../api/client";

interface AddStockFormValues {
  name: string;
  qty: number | string;
  unit: string;
  price: number | string;
  reorder_level: number | string;
}

interface EditFormValues {
  name: string;
  unit: string;
  reorder_level: number | string;
}

export default function InventoryPage() {
  const [search, setSearch] = useState("");
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Inventory | null>(null);
  const [confirmDeleteItem, setConfirmDeleteItem] = useState<Inventory | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const queryClient = useQueryClient();

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["inventory", search],
    queryFn: () => listInventory(search || undefined),
  });

  const addForm = useForm<AddStockFormValues>({
    initialValues: { name: "", qty: "", unit: "", price: "", reorder_level: "" },
    validate: {
      name: (v) => (String(v).trim().length === 0 ? "Name is required" : null),
      qty: (v) => (v === "" || Number(v) <= 0 ? "Qty must be > 0" : null),
      unit: (v) => (String(v).trim().length === 0 ? "Unit is required" : null),
      price: (v) => (v === "" || Number(v) < 0 ? "Price must be >= 0" : null),
    },
  });

  const editForm = useForm<EditFormValues>({
    initialValues: { name: "", unit: "", reorder_level: "" },
    validate: {
      name: (v) => (String(v).trim().length === 0 ? "Name is required" : null),
      unit: (v) => (String(v).trim().length === 0 ? "Unit is required" : null),
    },
  });

  function openAdd() {
    addForm.reset();
    setAddModalOpen(true);
  }

  function closeAdd() {
    setAddModalOpen(false);
    addForm.reset();
  }

  function openEdit(item: Inventory) {
    setEditingItem(item);
    editForm.setValues({ name: item.name, unit: item.unit, reorder_level: item.reorder_level });
  }

  function closeEdit() {
    setEditingItem(null);
    editForm.reset();
  }

  const addMutation = useMutation({
    mutationFn: (data: { name: string; qty: number; unit: string; price: number; reorder_level?: number }) =>
      addStock(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      notifications.show({ color: "green", title: "Success", message: "Stock added." });
      closeAdd();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to add stock.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; unit?: string; reorder_level?: number } }) =>
      updateInventory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      notifications.show({ color: "green", title: "Success", message: "Item updated." });
      closeEdit();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to update item.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteInventory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      notifications.show({ color: "green", title: "Success", message: "Item deleted." });
      setConfirmDeleteItem(null);
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to delete item.";
      notifications.show({ color: "red", title: "Error", message: msg });
      setConfirmDeleteItem(null);
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => resetInventory(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      notifications.show({ color: "green", title: "Reset complete", message: `${res.reset} items zeroed.` });
      setConfirmReset(false);
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to reset inventory.";
      notifications.show({ color: "red", title: "Error", message: msg });
      setConfirmReset(false);
    },
  });

  function handleAddSubmit(values: AddStockFormValues) {
    const payload: { name: string; qty: number; unit: string; price: number; reorder_level?: number } = {
      name: values.name.trim(),
      qty: Number(values.qty),
      unit: values.unit.trim(),
      price: Number(values.price),
    };
    if (values.reorder_level !== "" && values.reorder_level !== undefined) {
      payload.reorder_level = Number(values.reorder_level);
    }
    addMutation.mutate(payload);
  }

  function handleEditSubmit(values: EditFormValues) {
    if (!editingItem) return;
    const data: { name?: string; unit?: string; reorder_level?: number } = {
      name: values.name.trim(),
      unit: values.unit.trim(),
    };
    if (values.reorder_level !== "" && values.reorder_level !== undefined) {
      data.reorder_level = Number(values.reorder_level);
    }
    updateMutation.mutate({ id: editingItem.id, data });
  }

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={3}>Inventory</Title>
        <Group gap="xs">
          <Button color="red" variant="light" onClick={() => setConfirmReset(true)}>
            Reset
          </Button>
          <Button onClick={openAdd}>Add stock</Button>
        </Group>
      </Group>

      <TextInput
        placeholder="Search inventory..."
        value={search}
        onChange={(e) => setSearch(e.currentTarget.value)}
        mb="md"
        w={300}
      />

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Qty</Table.Th>
            <Table.Th>Unit</Table.Th>
            <Table.Th>Avg Price</Table.Th>
            <Table.Th>Reorder Level</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {isLoading && (
            <Table.Tr>
              <Table.Td colSpan={6}>Loading...</Table.Td>
            </Table.Tr>
          )}
          {!isLoading && items.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={6}>No items found.</Table.Td>
            </Table.Tr>
          )}
          {items.map((item) => {
            const isLow = item.reorder_level > 0 && item.qty <= item.reorder_level;
            return (
              <Table.Tr key={item.id}>
                <Table.Td>{item.name}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {item.qty}
                    {isLow && (
                      <Badge color="red" size="xs">
                        low
                      </Badge>
                    )}
                  </Group>
                </Table.Td>
                <Table.Td>{item.unit}</Table.Td>
                <Table.Td>{item.avg_price.toFixed(2)}</Table.Td>
                <Table.Td>{item.reorder_level}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" variant="light" onClick={() => openEdit(item)}>
                      Edit
                    </Button>
                    <ActionIcon
                      color="red"
                      variant="light"
                      size="sm"
                      onClick={() => setConfirmDeleteItem(item)}
                    >
                      ×
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>

      {/* Add Stock Modal */}
      <Modal opened={addModalOpen} onClose={closeAdd} title="Add stock">
        <form onSubmit={addForm.onSubmit(handleAddSubmit)}>
          <Stack>
            <TextInput
              label="Name"
              placeholder="Ingredient name"
              {...addForm.getInputProps("name")}
            />
            <NumberInput
              label="Qty"
              placeholder="Quantity"
              min={0}
              {...addForm.getInputProps("qty")}
            />
            <TextInput
              label="Unit"
              placeholder="e.g. kg, L, pcs"
              {...addForm.getInputProps("unit")}
            />
            <NumberInput
              label="Purchase price / unit"
              placeholder="0.00"
              min={0}
              decimalScale={2}
              {...addForm.getInputProps("price")}
            />
            <NumberInput
              label="Reorder level (optional)"
              placeholder="0"
              min={0}
              {...addForm.getInputProps("reorder_level")}
            />
            <Group justify="flex-end" mt="sm">
              <Button type="button" variant="default" onClick={closeAdd}>
                Cancel
              </Button>
              <Button type="submit" loading={addMutation.isPending}>
                Add stock
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Edit Modal */}
      <Modal opened={editingItem !== null} onClose={closeEdit} title="Edit item">
        <form onSubmit={editForm.onSubmit(handleEditSubmit)}>
          <Stack>
            <TextInput
              label="Name"
              placeholder="Ingredient name"
              {...editForm.getInputProps("name")}
            />
            <TextInput
              label="Unit"
              placeholder="e.g. kg, L, pcs"
              {...editForm.getInputProps("unit")}
            />
            <NumberInput
              label="Reorder level (optional)"
              placeholder="0"
              min={0}
              {...editForm.getInputProps("reorder_level")}
            />
            <Group justify="flex-end" mt="sm">
              <Button type="button" variant="default" onClick={closeEdit}>
                Cancel
              </Button>
              <Button type="submit" loading={updateMutation.isPending}>
                Save
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Confirm Delete Modal */}
      <Modal
        opened={confirmDeleteItem !== null}
        onClose={() => setConfirmDeleteItem(null)}
        title="Confirm Delete"
        size="sm"
      >
        <Text mb="md">
          Are you sure you want to delete <strong>{confirmDeleteItem?.name}</strong>?
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setConfirmDeleteItem(null)}>
            Cancel
          </Button>
          <Button
            color="red"
            loading={deleteMutation.isPending}
            onClick={() => confirmDeleteItem && deleteMutation.mutate(confirmDeleteItem.id)}
          >
            Delete
          </Button>
        </Group>
      </Modal>

      {/* Confirm Reset Modal */}
      <Modal
        opened={confirmReset}
        onClose={() => setConfirmReset(false)}
        title="Confirm Reset"
        size="sm"
      >
        <Text mb="md">
          This will zero all quantities and values for every item in inventory. This action cannot
          be undone.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setConfirmReset(false)}>
            Cancel
          </Button>
          <Button color="red" loading={resetMutation.isPending} onClick={() => resetMutation.mutate()}>
            Reset inventory
          </Button>
        </Group>
      </Modal>
    </Box>
  );
}
