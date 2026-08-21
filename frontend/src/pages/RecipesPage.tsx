import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  Title,
  NumberInput,
  Button,
  Group,
  Table,
  Modal,
  Select,
  Stack,
  ActionIcon,
  Text,
  Box,
} from "@mantine/core";
import {
  listRecipes,
  createRecipe,
  updateRecipe,
  deleteRecipe,
  listProducts,
  listInventory,
  ApiError,
  type Recipe,
} from "../api/client";

interface AddFormValues {
  product_id: string;
  ingredient_id: string;
  qty: number | string;
}

interface EditFormValues {
  qty: number | string;
}

export default function RecipesPage() {
  const [filterProductId, setFilterProductId] = useState<string | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editingRecipe, setEditingRecipe] = useState<Recipe | null>(null);
  const [confirmDeleteRecipe, setConfirmDeleteRecipe] = useState<Recipe | null>(null);
  const queryClient = useQueryClient();

  const productIdNum = filterProductId != null ? Number(filterProductId) : undefined;

  const { data: recipes = [], isLoading } = useQuery({
    queryKey: ["recipes", productIdNum],
    queryFn: () => listRecipes(productIdNum),
  });

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => listProducts(),
  });

  const { data: ingredients = [] } = useQuery({
    queryKey: ["inventory"],
    queryFn: () => listInventory(),
  });

  const productOptions = products.map((p) => ({ value: String(p.id), label: p.name }));
  const ingredientOptions = ingredients.map((i) => ({ value: String(i.id), label: i.name }));

  const addForm = useForm<AddFormValues>({
    initialValues: { product_id: "", ingredient_id: "", qty: "" },
    validate: {
      product_id: (v) => (v === "" ? "Product is required" : null),
      ingredient_id: (v) => (v === "" ? "Ingredient is required" : null),
      qty: (v) => (v === "" || Number(v) <= 0 ? "Qty must be > 0" : null),
    },
  });

  const editForm = useForm<EditFormValues>({
    initialValues: { qty: "" },
    validate: {
      qty: (v) => (v === "" || Number(v) <= 0 ? "Qty must be > 0" : null),
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

  function openEdit(recipe: Recipe) {
    setEditingRecipe(recipe);
    editForm.setValues({ qty: recipe.qty });
  }

  function closeEdit() {
    setEditingRecipe(null);
    editForm.reset();
  }

  const createMutation = useMutation({
    mutationFn: (data: { product_id: number; ingredient_id: number; qty: number }) =>
      createRecipe(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      notifications.show({ color: "green", title: "Success", message: "Recipe entry created." });
      closeAdd();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to create recipe.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { qty: number } }) =>
      updateRecipe(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      notifications.show({ color: "green", title: "Success", message: "Recipe entry updated." });
      closeEdit();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to update recipe.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteRecipe(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      notifications.show({ color: "green", title: "Success", message: "Recipe entry deleted." });
      setConfirmDeleteRecipe(null);
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to delete recipe.";
      notifications.show({ color: "red", title: "Error", message: msg });
      setConfirmDeleteRecipe(null);
    },
  });

  function handleAddSubmit(values: AddFormValues) {
    createMutation.mutate({
      product_id: Number(values.product_id),
      ingredient_id: Number(values.ingredient_id),
      qty: Number(values.qty),
    });
  }

  function handleEditSubmit(values: EditFormValues) {
    if (!editingRecipe) return;
    updateMutation.mutate({ id: editingRecipe.id, data: { qty: Number(values.qty) } });
  }

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={3}>Recipes</Title>
        <Button onClick={openAdd}>Add entry</Button>
      </Group>

      <Select
        placeholder="Filter by product (all)"
        data={productOptions}
        value={filterProductId}
        onChange={setFilterProductId}
        clearable
        mb="md"
        w={300}
      />

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Product</Table.Th>
            <Table.Th>Ingredient</Table.Th>
            <Table.Th>Qty</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {isLoading && (
            <Table.Tr>
              <Table.Td colSpan={4}>Loading...</Table.Td>
            </Table.Tr>
          )}
          {!isLoading && recipes.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={4}>No recipe entries found.</Table.Td>
            </Table.Tr>
          )}
          {recipes.map((r) => (
            <Table.Tr key={r.id}>
              <Table.Td>{r.product_name}</Table.Td>
              <Table.Td>{r.ingredient_name}</Table.Td>
              <Table.Td>{r.qty}</Table.Td>
              <Table.Td>
                <Group gap="xs">
                  <Button size="xs" variant="light" onClick={() => openEdit(r)}>
                    Edit
                  </Button>
                  <ActionIcon
                    color="red"
                    variant="light"
                    size="sm"
                    onClick={() => setConfirmDeleteRecipe(r)}
                  >
                    ×
                  </ActionIcon>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {/* Add Modal */}
      <Modal opened={addModalOpen} onClose={closeAdd} title="Add recipe entry">
        <form onSubmit={addForm.onSubmit(handleAddSubmit)}>
          <Stack>
            <Select
              label="Product"
              placeholder="Select product"
              data={productOptions}
              searchable
              {...addForm.getInputProps("product_id")}
            />
            <Select
              label="Ingredient"
              placeholder="Select ingredient"
              data={ingredientOptions}
              searchable
              {...addForm.getInputProps("ingredient_id")}
            />
            <NumberInput
              label="Qty"
              placeholder="0"
              min={0}
              {...addForm.getInputProps("qty")}
            />
            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={closeAdd}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending}>
                Create
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Edit Modal */}
      <Modal opened={editingRecipe !== null} onClose={closeEdit} title="Edit recipe entry">
        <form onSubmit={editForm.onSubmit(handleEditSubmit)}>
          <Stack>
            <Text size="sm" c="dimmed">
              {editingRecipe?.product_name} — {editingRecipe?.ingredient_name}
            </Text>
            <NumberInput
              label="Qty"
              placeholder="0"
              min={0}
              {...editForm.getInputProps("qty")}
            />
            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={closeEdit}>
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
        opened={confirmDeleteRecipe !== null}
        onClose={() => setConfirmDeleteRecipe(null)}
        title="Confirm Delete"
        size="sm"
      >
        <Text mb="md">
          Delete recipe entry for <strong>{confirmDeleteRecipe?.product_name}</strong> /{" "}
          <strong>{confirmDeleteRecipe?.ingredient_name}</strong>?
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setConfirmDeleteRecipe(null)}>
            Cancel
          </Button>
          <Button
            color="red"
            loading={deleteMutation.isPending}
            onClick={() => confirmDeleteRecipe && deleteMutation.mutate(confirmDeleteRecipe.id)}
          >
            Delete
          </Button>
        </Group>
      </Modal>
    </Box>
  );
}
