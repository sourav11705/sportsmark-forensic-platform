import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState(),
      child: const SportsMarkApp(),
    ),
  );
}

class AppState extends ChangeNotifier {
  final ApiService api = ApiService();
  List<dynamic> assets = [];
  List<dynamic> detections = [];

  AppState() {
    refresh();
  }

  Future<void> refresh() async {
    try {
      assets = await api.getAssets();
      detections = await api.getDetections();
      notifyListeners();
    } catch (e) {
      debugPrint("Error loading state: $e");
    }
  }
}

class SportsMarkApp extends StatelessWidget {
  const SportsMarkApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'SportsMark Dashboard',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0A0E17),
        primaryColor: const Color(0xFF00D4FF),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00D4FF),
          secondary: Color(0xFF00FF66),
          surface: Color(0xFF131A2A),
          background: Color(0xFF0A0E17),
        ),
        cardColor: const Color(0xFF131A2A),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF00D4FF),
            foregroundColor: const Color(0xFF0A0E17),
            textStyle: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
        ),
        snackBarTheme: const SnackBarThemeData(
          backgroundColor: Color(0xFF131A2A),
          contentTextStyle: TextStyle(color: Color(0xFF00FF66)),
        ),
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            backgroundColor: const Color(0xFF0D121E),
            selectedIndex: _selectedIndex,
            onDestinationSelected: (int index) {
              setState(() {
                _selectedIndex = index;
              });
              if (index == 3 || index == 0) {
                context.read<AppState>().refresh();
              }
            },
            selectedIconTheme: const IconThemeData(color: Color(0xFF00FF66)),
            unselectedIconTheme: const IconThemeData(color: Colors.white54),
            selectedLabelTextStyle: const TextStyle(color: Color(0xFF00FF66), fontWeight: FontWeight.bold),
            unselectedLabelTextStyle: const TextStyle(color: Colors.white54),
            labelType: NavigationRailLabelType.all,
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.security),
                label: Text('Asset Vault'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.podcasts),
                label: Text('Distribute'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.radar),
                label: Text('Piracy Scanner'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.gavel),
                label: Text('Enforcement'),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1, color: Color(0xFF1E2638)),
          Expanded(
            child: _buildTabView(_selectedIndex),
          ),
        ],
      ),
    );
  }

  Widget _buildTabView(int index) {
    switch (index) {
      case 0:
        return const AssetVaultView();
      case 1:
        return const DistributeView();
      case 2:
        return const PiracyScannerView();
      case 3:
        return const EnforcementView();
      default:
        return const Center(child: Text("Unknown Tab"));
    }
  }
}

// -----------------------------------------------------------------------------
// TAB VIEWS
// -----------------------------------------------------------------------------

class AssetVaultView extends StatefulWidget {
  const AssetVaultView({Key? key}) : super(key: key);
  @override
  _AssetVaultViewState createState() => _AssetVaultViewState();
}

class _AssetVaultViewState extends State<AssetVaultView> {
  bool _isUploading = false;
  Map<String, dynamic>? _lastUploadedAsset;

  Future<void> _uploadAsset() async {
    FilePickerResult? result = await FilePicker.pickFiles(type: FileType.video, withData: true);

    if (result != null && result.files.single.bytes != null) {
      setState(() => _isUploading = true);
      try {
        final api = context.read<AppState>().api;
        final response = await api.uploadAsset(
          'Raw Broadcast - ${DateTime.now().millisecondsSinceEpoch}',
          result.files.single.bytes!,
          result.files.single.name,
        );
        setState(() => _lastUploadedAsset = response);
        context.read<AppState>().refresh();
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Asset uploaded successfully!')));
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Upload failed: $e', style: const TextStyle(color: Colors.redAccent))));
      } finally {
        setState(() => _isUploading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Asset Vault', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 8),
          const Text('Securely upload and fingerprint raw broadcast feeds.', style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            onPressed: _isUploading ? null : _uploadAsset,
            icon: _isUploading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.black, strokeWidth: 2)) : const Icon(Icons.upload),
            label: Text(_isUploading ? 'Fingerprinting...' : 'Upload Raw Broadcast'),
          ),
          const SizedBox(height: 32),
          if (_lastUploadedAsset != null)
            Card(
              elevation: 8,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: Color(0xFF00FF66), width: 1)),
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.check_circle, color: Color(0xFF00FF66)),
                        SizedBox(width: 8),
                        Text('Asset Protected successfully', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF00FF66))),
                      ],
                    ),
                    const Divider(color: Colors.white24, height: 32),
                    Text('Asset ID: ${_lastUploadedAsset!['asset_id']}', style: const TextStyle(fontFamily: 'monospace', color: Colors.white)),
                    const SizedBox(height: 8),
                    Text('Frames Analyzed: ${_lastUploadedAsset!['frame_count']}', style: const TextStyle(color: Colors.white70)),
                    const SizedBox(height: 8),
                    Text('Master Hash: ${_lastUploadedAsset!['master_hash'].toString().substring(0, 32)}...', style: const TextStyle(color: Colors.white70)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class DistributeView extends StatefulWidget {
  const DistributeView({Key? key}) : super(key: key);
  @override
  _DistributeViewState createState() => _DistributeViewState();
}

class _DistributeViewState extends State<DistributeView> {
  bool _isDistributing = false;
  Map<String, dynamic>? _lastWatermark;
  String? _selectedAssetId;
  String _userId = 'user_999';
  String _platform = 'Web';

  Future<void> _distribute() async {
    if (_selectedAssetId == null) return;
    setState(() => _isDistributing = true);
    try {
      final api = context.read<AppState>().api;
      final response = await api.distributeAsset(_selectedAssetId!, _userId, _platform);
      setState(() => _lastWatermark = response);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Stream securely watermarked!')));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e', style: const TextStyle(color: Colors.redAccent))));
    } finally {
      setState(() => _isDistributing = false);
    }
  }

  Future<void> _downloadVideo() async {
    if (_lastWatermark == null) return;
    final sessionId = _lastWatermark!['session_id'];
    try {
      final uri = Uri.parse('${ApiService.baseUrl}/distribute/watermark/download/$sessionId');
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not launch download URL')));
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e', style: const TextStyle(color: Colors.redAccent))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final assets = context.watch<AppState>().assets;

    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Distribute', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 8),
          const Text('Generate forensically watermarked video streams for end users.', style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 32),
          if (assets.isEmpty) const Text('No assets available. Upload in Vault first.', style: TextStyle(color: Colors.orangeAccent)),
          if (assets.isNotEmpty)
            DropdownButton<String>(
              dropdownColor: const Color(0xFF131A2A),
              hint: const Text('Select Asset'),
              value: _selectedAssetId,
              items: assets.map<DropdownMenuItem<String>>((a) {
                return DropdownMenuItem<String>(
                  value: a['asset_id'],
                  child: Text('${a['title']} (${a['asset_id']})'),
                );
              }).toList(),
              onChanged: (val) => setState(() => _selectedAssetId = val),
            ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: (_isDistributing || _selectedAssetId == null) ? null : _distribute,
            icon: _isDistributing ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.black, strokeWidth: 2)) : const Icon(Icons.water_drop),
            label: Text(_isDistributing ? 'Embedding...' : 'Generate Protected Stream'),
          ),
          const SizedBox(height: 32),
          if (_lastWatermark != null)
            Card(
              elevation: 8,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: Color(0xFF00D4FF), width: 1)),
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Stream Generated', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF00D4FF))),
                    const Divider(color: Colors.white24, height: 32),
                    Text('Session ID: ${_lastWatermark!['session_id']}', style: const TextStyle(fontFamily: 'monospace', color: Colors.white)),
                    Text('Target User: ${_lastWatermark!['user_id']}', style: const TextStyle(color: Colors.white70)),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: _downloadVideo,
                      icon: const Icon(Icons.download, color: Color(0xFF00D4FF)),
                      label: const Text('Download Watermarked Video', style: TextStyle(color: Color(0xFF00D4FF))),
                      style: OutlinedButton.styleFrom(side: const BorderSide(color: Color(0xFF00D4FF))),
                    )
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class PiracyScannerView extends StatefulWidget {
  const PiracyScannerView({Key? key}) : super(key: key);
  @override
  _PiracyScannerViewState createState() => _PiracyScannerViewState();
}

class _PiracyScannerViewState extends State<PiracyScannerView> with SingleTickerProviderStateMixin {
  bool _isScanning = false;
  Map<String, dynamic>? _scanResult;
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(vsync: this, duration: const Duration(milliseconds: 1000))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _scanSuspectVideo() async {
    final assets = context.read<AppState>().assets;
    if (assets.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No assets in registry to compare against.')));
      return;
    }

    FilePickerResult? result = await FilePicker.pickFiles(type: FileType.video, withData: true);
    if (result != null && result.files.single.bytes != null) {
      setState(() {
        _isScanning = true;
        _scanResult = null;
      });
      try {
        final api = context.read<AppState>().api;
        // In a real app we'd scan against all, or let user pick. For demo, we use the first asset.
        String assetId = assets.first['asset_id']; 
        final response = await api.scanVideo(assetId, result.files.single.bytes!, result.files.single.name);
        setState(() => _scanResult = response);
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Scan failed: $e', style: const TextStyle(color: Colors.redAccent))));
      } finally {
        setState(() => _isScanning = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Piracy Scanner', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 8),
          const Text('Upload suspect video clips for deep forensic analysis.', style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 32),
          GestureDetector(
            onTap: _isScanning ? null : _scanSuspectVideo,
            child: Container(
              height: 200,
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFF0D121E),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: _isScanning ? const Color(0xFF00FF66) : const Color(0xFF1E2638), width: 2),
              ),
              child: Center(
                child: _isScanning
                    ? FadeTransition(
                        opacity: _pulseController,
                        child: const Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.radar, size: 48, color: Color(0xFF00FF66)),
                            SizedBox(height: 16),
                            Text('PERFORMING FORENSIC SCAN...', style: TextStyle(color: Color(0xFF00FF66), fontWeight: FontWeight.bold, letterSpacing: 2)),
                          ],
                        ),
                      )
                    : const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.cloud_upload, size: 48, color: Colors.white54),
                          SizedBox(height: 16),
                          Text('Upload Suspect Video', style: TextStyle(color: Colors.white54, fontSize: 18)),
                        ],
                      ),
              ),
            ),
          ),
          const SizedBox(height: 32),
          if (_scanResult != null) _buildResultCard(),
        ],
      ),
    );
  }

  Widget _buildResultCard() {
    bool isMatch = _scanResult!['detection_logged'] == true;
    final wm = _scanResult!['watermark'];
    final fp = _scanResult!['fingerprint'];
    
    if (!isMatch) {
      return Card(
        color: const Color(0xFF1A1A1A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8), side: const BorderSide(color: Colors.grey)),
        child: const Padding(
          padding: EdgeInsets.all(24.0),
          child: Text('NO MATCH DETECTED. File appears clean.', style: TextStyle(color: Colors.white)),
        ),
      );
    }

    String extractedId = wm != null && wm['session_id'] != null ? wm['session_id'] : 'UNKNOWN (Perceptual Match Only)';
    
    return Card(
      elevation: 16,
      color: const Color(0xFF2A0000),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: Colors.redAccent, width: 2)),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 32),
                SizedBox(width: 16),
                Text('WATERMARK DETECTED: UNAUTHORIZED COPY', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.redAccent)),
              ],
            ),
            const Divider(color: Colors.redAccent, height: 32),
            Text('Extracted Session ID: $extractedId', style: const TextStyle(fontFamily: 'monospace', color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text('Fingerprint Similarity: ${(fp['similarity'] * 100).toStringAsFixed(1)}%', style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 8),
            Text('Original Asset ID: ${fp['asset_id']}', style: const TextStyle(color: Colors.white70)),
          ],
        ),
      ),
    );
  }
}

class EnforcementView extends StatefulWidget {
  const EnforcementView({Key? key}) : super(key: key);
  @override
  _EnforcementViewState createState() => _EnforcementViewState();
}

class _EnforcementViewState extends State<EnforcementView> {
  bool _isGenerating = false;

  Future<void> _generateDMCA(String detectionId) async {
    setState(() => _isGenerating = true);
    try {
      final api = context.read<AppState>().api;
      final response = await api.generateDMCA(detectionId);
      final text = response['notice_text'];
      
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          backgroundColor: const Color(0xFF1A1A1A),
          title: const Text('DMCA Takedown Notice', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          content: Container(
            width: 600,
            height: 400,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF0D121E),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.white24),
            ),
            child: SingleChildScrollView(
              child: SelectableText(
                text,
                style: const TextStyle(color: Colors.white70, fontFamily: 'monospace', fontSize: 13),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close', style: TextStyle(color: Colors.white54)),
            ),
            ElevatedButton.icon(
              onPressed: () async {
                final uri = Uri.parse('${ApiService.baseUrl}/dmca/download/$detectionId');
                if (await canLaunchUrl(uri)) {
                  await launchUrl(uri);
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not launch PDF download')));
                }
              },
              icon: const Icon(Icons.picture_as_pdf, size: 18),
              label: const Text('Download PDF'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to generate DMCA: $e', style: const TextStyle(color: Colors.redAccent))));
    } finally {
      setState(() => _isGenerating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detections = context.watch<AppState>().detections;

    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Enforcement', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 8),
          const Text('Automated DMCA takedown notice generation.', style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 32),
          if (detections.isEmpty) const Text('No piracy detections logged yet.', style: TextStyle(color: Colors.white54)),
          Expanded(
            child: ListView.builder(
              itemCount: detections.length,
              itemBuilder: (context, index) {
                final d = detections[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: Color(0xFF1E2638))),
                  child: ListTile(
                    contentPadding: const EdgeInsets.all(16),
                    leading: const Icon(Icons.report, color: Colors.redAccent, size: 36),
                    title: Text('Detection: ${d['detection_id']}'),
                    subtitle: Text('Asset: ${d['asset_id']} | Platform: ${d['platform']} | Date: ${d['detected_at'].toString().substring(0, 10)}'),
                    trailing: ElevatedButton.icon(
                      onPressed: _isGenerating ? null : () => _generateDMCA(d['detection_id']),
                      icon: const Icon(Icons.gavel, size: 18),
                      label: const Text('Generate One-Click DMCA'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.redAccent,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      ),
                    ),
                  ),
                );
              },
            ),
          )
        ],
      ),
    );
  }
}
