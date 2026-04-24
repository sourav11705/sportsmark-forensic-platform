import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:8000';

  Future<Map<String, dynamic>> uploadAsset(String title, List<int> fileBytes, String filename) async {
    var uri = Uri.parse('$baseUrl/assets/register');
    var request = http.MultipartRequest('POST', uri)
      ..fields['title'] = title
      ..files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: filename,
        contentType: MediaType('video', 'mp4'),
      ));
    var response = await request.send();
    var responseBody = await response.stream.bytesToString();
    if (response.statusCode == 200) {
      return jsonDecode(responseBody);
    } else {
      throw Exception('Failed to upload asset: $responseBody');
    }
  }

  Future<Map<String, dynamic>> distributeAsset(String assetId, String userId, String platform) async {
    var uri = Uri.parse('$baseUrl/distribute/watermark');
    var response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'asset_id': assetId,
        'user_id': userId,
        'platform': platform,
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to distribute asset: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> scanVideo(String assetId, List<int> fileBytes, String filename) async {
    var uri = Uri.parse('$baseUrl/detect/full');
    var request = http.MultipartRequest('POST', uri)
      ..fields['asset_id'] = assetId
      ..files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: filename,
        contentType: MediaType('video', 'mp4'),
      ));
    var response = await request.send();
    var responseBody = await response.stream.bytesToString();
    if (response.statusCode == 200) {
      return jsonDecode(responseBody);
    } else {
      throw Exception('Failed to scan video: $responseBody');
    }
  }

  Future<Map<String, dynamic>> generateDMCA(String detectionId) async {
    var uri = Uri.parse('$baseUrl/dmca/generate');
    var response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'detection_id': detectionId,
        'organization': 'SportsMark Global',
        'contact_email': 'legal@sportsmark.com',
        'address': '123 IP Lane, Tech City',
        'signatory': 'Chief Legal Officer',
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to generate DMCA: ${response.body}');
    }
  }

  Future<List<dynamic>> getAssets() async {
    var uri = Uri.parse('$baseUrl/assets/');
    var response = await http.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load assets');
    }
  }

  Future<List<dynamic>> getDetections() async {
    var uri = Uri.parse('$baseUrl/detect/detections');
    var response = await http.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load detections');
    }
  }
}
