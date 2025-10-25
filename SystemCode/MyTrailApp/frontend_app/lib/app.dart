import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'screens/map/mytrail_map_screen.dart';

class MyTrailApp extends ConsumerWidget {
  const MyTrailApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'MyTrail',
      theme: AppTheme.lightTheme,
      home: const MyTrailMapScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
