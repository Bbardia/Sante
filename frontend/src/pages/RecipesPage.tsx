import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  Title,
  NumberInput,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  ActionIcon,
  Text,
  Box,
  Card,
  SimpleGrid,
} from "@mantine/core";
import {
  listRecipes,
  listProducts,
  listInventory,
  setProductRecipe,
  ApiError,
  type Product,
} from "../api/client";

interface RowType {
  ingredient_id: string;
  qty: number | string;
}

interface EditorFormValues {
  rows: RowType[];
}

export default function RecipesPage() {
  const [editorProduct, setEditorProduct] = useState<Product | null>(null);
  const queryClient = useQueryClient();

  const { data: recipes = [], isLoading: recipesLoading } = useQuery({
    queryKey: ["recipes"],
    queryFn: () => listRecipes(),
  });

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => listProducts(),
  });

  const { data: inventory = [] } = useQuery({
    queryKey: ["inventory"],
    queryFn: () => listInventory(),
  });

  // Map ingredient id → { name, unit }
  const ingredientById = useMemo(() => {
    const m = new Map<number, { name: string; unit: string }>();
    for (const item of inventory) m.set(item.id, { name: item.name, unit: item.unit });
    return m;
  }, [inventory]);

  // Group all recipes by product_id
  const recipesByProduct = useMemo(() => {
    const m = new Map<number, typeof recipes>();
    for (const r of recipes) {
      const existing = m.get(r.product_id) ?? [];
      existing.push(r);
      m.set(r.product_id, existing);
    }
    return m;
  }, [recipes]);

  const ingredientOptions = inventory.map((i) => ({ value: String(i.id), label: i.name }));
  const productSelectOptions = products.map((p) => ({ value: String(p.id), label: p.name }));

  const form = useForm<EditorFormValues>({
    initialValues: { rows: [] },
  });

  function openEditor(product: Product) {
    const existing = recipesByProduct.get(product.id) ?? [];
    const rows: RowType[] =
      existing.length > 0
        ? existing.map((r) => ({ ingredient_id: String(r.ingredient_id), qty: r.qty }))
        : [{ ingredient_id: "", qty: "" }];
    form.setValues({ rows });
    setEditorProduct(product);
  }

  function closeEditor() {
    setEditorProduct(null);
    form.reset();
  }

  const saveMutation = useMutation({
    mutationFn: ({ productId, rows }: { productId: number; rows: RowType[] }) => {
      const items = rows
        .filter((r) => r.ingredient_id !== "")
        .map((r) => ({ ingredient_id: Number(r.ingredient_id), qty: Number(r.qty) }));
      return setProductRecipe(productId, items);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      notifications.show({ color: "green", title: "Saved", message: "Recipe saved successfully." });
      closeEditor();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to save recipe.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  function handleSave(values: EditorFormValues) {
    if (!editorProduct) return;

    // Drop rows with no ingredient selected
    const validRows = values.rows.filter((r) => r.ingredient_id !== "");

    // Check qty > 0 for all valid rows
    for (const r of validRows) {
      if (r.qty === "" || Number(r.qty) <= 0) {
        notifications.show({
          color: "red",
          title: "Validation error",
          message: "All ingredient quantities must be greater than 0.",
        });
        return;
      }
    }

    // Check for duplicate ingredients
    const seen = new Set<string>();
    for (const r of validRows) {
      if (seen.has(r.ingredient_id)) {
        const ing = ingredientById.get(Number(r.ingredient_id));
        notifications.show({
          color: "red",
          title: "Duplicate ingredient",
          message: `"${ing?.name ?? r.ingredient_id}" appears more than once.`,
        });
        return;
      }
      seen.add(r.ingredient_id);
    }

    saveMutation.mutate({ productId: editorProduct.id, rows: validRows });
  }

  // Products that have at least one recipe row
  const productsWithRecipes = products.filter((p) => (recipesByProduct.get(p.id)?.length ?? 0) > 0);

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={3}>Recipes</Title>
      </Group>

      {/* Top control: open editor for any product */}
      <Select
        placeholder="Edit recipe for product…"
        data={productSelectOptions}
        searchable
        clearable
        value={null}
        onChange={(val) => {
          if (!val) return;
          const product = products.find((p) => String(p.id) === val);
          if (product) openEditor(product);
        }}
        mb="xl"
        w={320}
      />

      {/* Cards: one per product that has recipes */}
      {recipesLoading && (
        <Text c="dimmed">Loading…</Text>
      )}

      {!recipesLoading && productsWithRecipes.length === 0 && (
        <Text c="dimmed">No recipes yet — pick a product above to add one.</Text>
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
        {productsWithRecipes.map((product) => {
          const rows = recipesByProduct.get(product.id) ?? [];
          return (
            <Card key={product.id} withBorder shadow="sm" radius="md" padding="md">
              <Group justify="space-between" mb="sm">
                <Text fw={600}>{product.name}</Text>
                <Button size="xs" variant="light" onClick={() => openEditor(product)}>
                  Edit recipe
                </Button>
              </Group>
              <Stack gap={4}>
                {rows.map((r) => {
                  const ing = ingredientById.get(r.ingredient_id);
                  return (
                    <Group key={r.id} justify="space-between">
                      <Text size="sm">{r.ingredient_name}</Text>
                      <Text size="sm" c="dimmed">
                        {r.qty} {ing?.unit ?? ""}
                      </Text>
                    </Group>
                  );
                })}
              </Stack>
            </Card>
          );
        })}
      </SimpleGrid>

      {/* Editor Modal */}
      <Modal
        opened={editorProduct !== null}
        onClose={closeEditor}
        title={editorProduct ? `Recipe for: ${editorProduct.name}` : "Recipe"}
        size="lg"
      >
        <form onSubmit={form.onSubmit(handleSave)}>
          <Stack>
            {form.values.rows.map((row, i) => {
              const selectedUnit =
                row.ingredient_id !== ""
                  ? (ingredientById.get(Number(row.ingredient_id))?.unit ?? "")
                  : "";
              return (
                <Group key={i} align="flex-end" gap="sm">
                  <Select
                    label={i === 0 ? "Ingredient" : undefined}
                    placeholder="Select ingredient"
                    data={ingredientOptions}
                    searchable
                    style={{ flex: 1 }}
                    {...form.getInputProps(`rows.${i}.ingredient_id`)}
                  />
                  <NumberInput
                    label={i === 0 ? "Qty" : undefined}
                    placeholder="0"
                    min={0}
                    style={{ width: 90 }}
                    {...form.getInputProps(`rows.${i}.qty`)}
                  />
                  <Text
                    size="sm"
                    c="dimmed"
                    style={{ width: 48, paddingBottom: 6 }}
                  >
                    {selectedUnit}
                  </Text>
                  <ActionIcon
                    type="button"
                    color="red"
                    variant="light"
                    style={{ marginBottom: 2 }}
                    onClick={() => form.removeListItem("rows", i)}
                    aria-label="Remove row"
                  >
                    ×
                  </ActionIcon>
                </Group>
              );
            })}

            <Button
              type="button"
              variant="subtle"
              size="sm"
              onClick={() => form.insertListItem("rows", { ingredient_id: "", qty: "" })}
            >
              + Add ingredient
            </Button>

            <Group justify="flex-end" mt="sm">
              <Button type="button" variant="default" onClick={closeEditor}>
                Cancel
              </Button>
              <Button type="submit" loading={saveMutation.isPending}>
                Save recipe
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Box>
  );
}
