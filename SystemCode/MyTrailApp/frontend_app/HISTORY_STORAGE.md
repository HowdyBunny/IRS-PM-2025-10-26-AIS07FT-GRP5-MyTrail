# MyTrail Local History Storage

This document describes the local history storage implementation for the MyTrail app using a "files + index.json" approach.

## Overview

The local history storage system stores search results locally on the device without requiring user login. It provides fast loading, nearby queries, deduplication, and capacity management.

## Architecture

### Directory Structure
```
<app-documents>/
├── index.json          # Metadata index (newest first)
└── routes/             # Individual route files
    ├── abcd1234ef567890.json
    ├── beef5678cafe9012.json
    └── ...
```

### Core Components

1. **`lib/history/models.dart`**
   - `Constraints`: Input parameters for trail searches
   - `HistoryIndexItem`: Metadata entries in index.json

2. **`lib/history/json_hash.dart`**
   - JSON canonicalization utilities
   - SHA256 hashing for constraint deduplication

3. **`lib/history/history_repository.dart`**
   - Main repository class with all storage operations
   - Thread-safe operations using synchronized locks
   - Atomic file writes to prevent corruption

4. **`lib/features/history/providers/local_history_provider.dart`**
   - Riverpod provider for local history state management
   - Connects repository to UI layer
   - Handles loading, saving, and querying operations

## Integration with App

### ✅ Automatic History Saving
When users perform route searches, the app now automatically:
1. Calls the backend API for route suggestions
2. Saves the successful response to local history storage
3. Deduplicates based on search constraints
4. Enforces 30-item capacity limit

### ✅ History Screen Updates
The history screen now:
- Uses **local storage** instead of server API calls
- Shows search metadata (location, distance, duration, elevation)
- Displays creation timestamp and picked routes
- Loads instantly from local files

### ✅ Updated Navigation
- History icon in map screen navigates to local history
- No network calls required for viewing history
- Offline-first experience

## Key Features

### ✅ Deduplication
- Uses SHA256 hash of canonicalized constraints JSON
- Same search parameters result in same hash
- Overwrites existing data when constraints match

### ✅ Capacity Management
- Automatically enforces maximum of 30 stored items
- Removes oldest entries when capacity exceeded
- Deletes corresponding route files when pruning

### ✅ Fast Queries
- Index loading sorted by creation date (newest first)
- Nearby search using Haversine distance calculation
- Direct ID-based payload retrieval

### ✅ Thread Safety
- All write operations protected by synchronized locks
- Atomic file writes prevent corruption
- Graceful handling of concurrent access

### ✅ Error Resilience
- Graceful handling of corrupted index files
- Best-effort deletion of old files
- No exceptions thrown for normal IO problems

## API Usage

### Initialize Repository
```dart
final repo = await HistoryRepository.create();
```

### Save Search Results
```dart
final item = await repo.saveSearch(
  constraints: Constraints(
    lat: 1.2966,
    lng: 103.7764,
    radiusKm: 5.0,
    durationMin: 30,
    includeCategories: ['park', 'waterfront'],
    avoidCategories: ['retail_core'],
    petFriendly: true,
    elevationGainMinM: 40,
    routeType: 'loop',
  ),
  routesResponse: backendApiResponse,
);
```

### Load History
```dart
final history = await repo.loadIndex(); // Newest first
```

### Query Nearby Searches
```dart
final nearby = await repo.queryNearby(
  lat: 1.2970,
  lng: 103.7770,
  withinKm: 2.0,
);
```

### Read Full Route Data
```dart
final payload = await repo.readRoutesPayload(item);
final routes = payload?['routes'] as List?;
```

### Mark Picked Route
```dart
await repo.setPickedRoute(item.id, 'r2');
```

### Capacity Management
```dart
await repo.pruneByMaxItems(30); // Enforce max 30 items
await repo.clearAll();          // Clear all data
```

## Testing

Comprehensive test suite covers:
- ✅ Basic save/load operations
- ✅ Deduplication behavior
- ✅ Capacity enforcement (30 item limit)
- ✅ Nearby distance filtering
- ✅ Picked route marking
- ✅ Data clearing
- ✅ Corrupted index handling
- ✅ Atomic operations

Run tests:
```bash
flutter test test/history_repository_test.dart
```

## Performance Characteristics

- **Storage**: Efficient JSON files with gzip-like compression potential
- **Memory**: Lazy loading of route payloads (index only in memory)
- **Speed**: O(1) ID lookups, O(n) nearby queries where n ≤ 30
- **Thread Safety**: Synchronized operations prevent race conditions

## Platform Support

- ✅ **Android**: Uses `getApplicationDocumentsDirectory()`
- ✅ **iOS**: Uses `getApplicationDocumentsDirectory()`
- ✅ **No platform-specific code** beyond `path_provider`

## Dependencies

```yaml
dependencies:
  path_provider: ^2.1.2   # Cross-platform file paths
  crypto: ^3.0.3          # SHA256 hashing
  synchronized: ^3.1.0    # Async locks

dev_dependencies:
  flutter_test: sdk       # Testing framework
```

## Integration with Riverpod

The repository is designed to be easily integrated with Riverpod providers:

```dart
final historyRepositoryProvider = Provider<HistoryRepository>((ref) {
  throw UnimplementedError('HistoryRepository not initialized');
});

final historyProvider = FutureProvider<List<HistoryIndexItem>>((ref) async {
  final repo = ref.read(historyRepositoryProvider);
  return repo.loadIndex();
});
```

## Future Enhancements

Potential improvements:
- Compression of large route payloads
- Background sync with cloud storage
- Search result caching strategies
- Offline-first architecture patterns