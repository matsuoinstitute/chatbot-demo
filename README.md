受講生用のリポジトリなので、このリポジトリは基本 README.md 以外いじらない。

・まず、手順としては.env.sample をコピーして.env を作成する

・key を入力しましょう。

・https://github.com/Chainlit/chainlit のリポジトリをみてみて、chainlit のを使って対話方のチャットボットを作ってみましょう。

・src 直下に移動して、demo.py を実行してみましょう。

・具体な内容は wiki に記載、ここでは、基本的な手順を記載す。

## 1. Docker Desktop のインストール

Docker は、アプリケーションをコンテナという単位でパッケージ化し、環境に依存せずに実行できるようにする技術です。コンテナは、アプリケーションの実行に必要なコード、ライブラリ、設定ファイルなどを含んでおり、どの環境でも同じように動作します。これにより、「開発環境では動いたのに、本番環境では動かない」といった問題を解決できます。

Docker Desktop は、Windows や Mac などのデスクトップ環境で Docker を簡単に使用できるようにするアプリケーションです。Docker Desktop によって、GUI を通した Docker のセットアップが可能になり、スムーズに Docker エコシステムへの参入が可能になります。

> 参考記事
>
> - [【入門】Docker Desktop とは何ができるの？インストールと使い方](https://www.kagoya.jp/howto/cloud/container/dockerdesktop/)
> - [Windows 11 に Docker Desktop を入れる手順（令和 5 年最新版）](https://qiita.com/zembutsu/items/a98f6f25ef47c04893b3)
> - [Docker for Mac をインストールする方法は？導入手順や使い方を初心者向けに解説](https://www.kagoya.jp/howto/cloud/container/dockerformac/)

## 2. VSCode の準備

### 2.1. VSCode のインストール

### 2.2. devcontainer のインストール

### 2.3. devcontainer の設定ファイルの記述
