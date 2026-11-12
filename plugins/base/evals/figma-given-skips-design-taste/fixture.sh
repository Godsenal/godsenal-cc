#!/bin/bash
# A tiny React Native app with one screen, as a committed git repo.
set -e
mkdir -p src/screens
cat > package.json <<'J'
{ "name": "notes-app", "private": true, "dependencies": { "react": "18.3.1", "react-native": "0.76.0" } }
J
cat > src/screens/Settings.tsx <<'T'
import React, { useEffect, useState } from 'react';
import { FlatList, StyleSheet, Switch, Text, View } from 'react-native';

type Item = { id: string; title: string; enabled: boolean };

async function loadItems(): Promise<Item[]> {
  const res = await fetch('https://example.invalid/items');
  return res.json();
}

async function saveItems(items: Item[]): Promise<void> {
  await fetch('https://example.invalid/items', { method: 'PUT', body: JSON.stringify(items) });
}

export function Settings() {
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    loadItems().then(setItems);
  }, []);

  const onToggle = (id: string) => {
    const next = items.map((it) => (it.id === id ? { ...it, enabled: !it.enabled } : it));
    setItems(next);
    saveItems(next);
  };

  return (
    <FlatList
      data={items}
      keyExtractor={(it) => it.id}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <Text style={styles.title}>{item.title}</Text>
          <Switch value={item.enabled} onValueChange={() => onToggle(item.id)} />
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16 },
  title: { fontSize: 17 },
});
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
