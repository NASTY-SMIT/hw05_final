from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post, User
from yatube.settings import POSTS_PER_PAGE


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Name')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post_list = []
        for i in range(13):
            cls.post_list.append(Post(text=f'Тестовый текст-{i}',
                                      group=cls.group,
                                      author=cls.user))
        Post.objects.bulk_create(cls.post_list)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)
        cache.clear()

    def test_first_page_contains_ten_records(self):
        paginator_views_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_name in paginator_views_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, 200)
                self.assertTrue('page_obj' in response.context)
                self.assertTrue(len(response.context['page_obj'])
                                == POSTS_PER_PAGE)

    def test_second_page_contains_three_records(self):
        paginator_views_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_name in paginator_views_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name + '?page=2')
                self.assertEqual(response.status_code, 200)
                self.assertTrue('page_obj' in response.context)
                self.assertEqual(len(response.context['page_obj']),
                                 Post.objects.count() - POSTS_PER_PAGE)

    def test_post_correct_appear(self):
        """Созданный пост отображается на нужных страницах"""
        self.user_3 = User.objects.create_user(username='Author')
        self.author = Client()
        self.author.force_login(self.user_3)
        post = Post.objects.create(
            text='test-text',
            author=self.user_3,
            group=self.group
        )
        pages_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': self.user_3}),
        ]
        for reverse_name in pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertIn(response.context['page_obj'][0].text, post.text)
