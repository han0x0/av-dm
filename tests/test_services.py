"""
服务层测试
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.services.freshrss import FreshRSSClient, FreshRSSItem
from app.services.bitcomet import BitCometClient, BitCometTask
from app.services.javsp import JavSPClient


class TestFreshRSSClient:
    """FreshRSS 客户端测试"""
    
    @pytest_asyncio.fixture
    async def client(self):
        client = FreshRSSClient()
        client.client = AsyncMock()
        yield client
    
    @pytest.mark.asyncio
    async def test_login(self, client):
        """测试登录"""
        mock_response = Mock()
        mock_response.text = "SID=xxx\nLSID=yyy\nAuth=test_token_123"
        client.client.post.return_value = mock_response
        
        token = await client.login()
        
        assert token == "test_token_123"
        assert client.auth_token == "test_token_123"
    
    @pytest.mark.asyncio
    async def test_get_starred_items(self, client):
        """测试获取 Starred items"""
        client.auth_token = "test_token"
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "tag:google.com,2005:reader/item/123",
                    "id_entry": 456,
                    "title": "Test Title",
                    "summary": {"content": "magnet:?xt=urn:btih:ABC123 Test 300MIUM-1334"}
                }
            ]
        }
        client.client.get.return_value = mock_response
        
        items = await client.get_starred_items()
        
        assert len(items) == 1
        assert items[0].title == "Test Title"
        assert items[0].uid == "300MIUM-1334"


class TestFreshRSSItem:
    """FreshRSSItem 数据类测试"""
    
    def test_extract_magnet(self):
        """测试磁力链接提取"""
        content = 'Some text magnet:?xt=urn:btih:ABC123&dn=test more text'
        item = FreshRSSItem(
            item_id="test",
            id_entry=1,
            title="Test",
            content=content
        )
        magnet = item._extract_magnet(content)
        assert magnet == "magnet:?xt=urn:btih:ABC123&dn=test"
    
    def test_extract_uid(self):
        """测试番号提取"""
        test_cases = [
            ("Title 300MIUM-1334 magnet", "300MIUM-1334"),
            ("ABP-123 Some text", "ABP-123"),
            ("title: 300MIUM1334", "300MIUM-1334"),
        ]
        
        for content, expected in test_cases:
            item = FreshRSSItem(
                item_id="test",
                id_entry=1,
                title="Test",
                content=content
            )
            uid = item._extract_uid(content)
            assert uid == expected, f"Failed for: {content}"


class TestBitCometTask:
    """BitCometTask 数据类测试"""
    
    def test_progress_percent(self):
        """测试进度百分比计算"""
        task = BitCometTask(
            task_id=1,
            task_name="Test",
            status="running",
            permillage=750,
            total_size=1000,
            selected_downloaded_size=750,
        )
        assert task.progress_percent == 75.0
    
    def test_is_completed(self):
        """测试完成状态判断"""
        task_completed = BitCometTask(
            task_id=1,
            task_name="Test",
            status="running",
            permillage=1000,
            total_size=1000,
            selected_downloaded_size=1000,
        )
        assert task_completed.is_completed is True
        
        task_running = BitCometTask(
            task_id=2,
            task_name="Test",
            status="running",
            permillage=500,
            total_size=1000,
            selected_downloaded_size=500,
        )
        assert task_running.is_completed is False
