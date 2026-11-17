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
mkdir -p profiles
cat > profiles/slow-start.cpuprofile <<'P'
{"nodes":[{"id":1,"callFrame":{"functionName":"(root)","scriptId":"0","url":"","lineNumber":-1,"columnNumber":-1},"hitCount":0,"children":[2,3]},{"id":2,"callFrame":{"functionName":"parseAllItems","scriptId":"7","url":"src/store/items.ts","lineNumber":41,"columnNumber":2},"hitCount":812},{"id":3,"callFrame":{"functionName":"render","scriptId":"9","url":"src/screens/Settings.tsx","lineNumber":20,"columnNumber":0},"hitCount":37}],"startTime":0,"endTime":849000,"samples":[2,2,2,3,2],"timeDeltas":[1000,1000,1000,1000,1000]}
P
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
