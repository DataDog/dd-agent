# MIT LICENSE

# Copyright (c) 2013 Travis CI GmbH <contact@travis-ci.org>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Original file:
# https://github.com/travis-ci/travis-build/blob/d1c3be0b6aec5989872f9c534185585108125d0d/lib/travis/build/script/shared/directory_cache/s3.rb

require 'digest/md5'
require 'shellwords'

require './ci/resources/cache/aws4_signature'

class Cache
  MSGS = {
    config_missing: 'Worker S3 config missing: %s'
  }.freeze

  VALIDATE = {
    bucket:            'bucket name',
    access_key_id:     'access key id',
    secret_access_key: 'secret access key'
  }.freeze

  CURL_FORMAT = "<<-EOF
     time_namelookup:  %{time_namelookup} s
        time_connect:  %{time_connect} s
     time_appconnect:  %{time_appconnect} s
    time_pretransfer:  %{time_pretransfer} s
       time_redirect:  %{time_redirect} s
  time_starttransfer:  %{time_starttransfer} s
      speed_download:  %{speed_download} bytes/s
       url_effective:  %{url_effective}
                     ----------
          time_total:  %{time_total} s
  EOF".freeze

  KeyPair = Struct.new(:id, :secret)

  Location = Struct.new(:scheme, :region, :bucket, :path) do
    def hostname
      "#{bucket}.#{region == 'us-east-1' ? 's3' : "s3-#{region}"}.amazonaws.com"
    end
  end

  CASHER_URL = 'https://raw.githubusercontent.com/DataDog/casher/%s/bin/casher'.freeze
  USE_RUBY   = '1.9.3'.freeze
  BIN_PATH   = '$DD_CASHER_DIR/bin/casher'.freeze

  attr_reader :data, :slug, :start, :msgs
  attr_accessor :directories

  def initialize(data, start = Time.now)
    @data = data
    @start = start
    @msgs = []
    @slug = ENV['TRAVIS_FLAVOR']
    @slug += '-' + ENV['FLAVOR_VERSION'] if ENV['FLAVOR_VERSION']
    # the cached artifacts depend on the CI file version
    @slug += '-' + Digest::MD5.hexdigest(File.read("#{ENV['TRAVIS_BUILD_DIR']}/ci/#{ENV['TRAVIS_FLAVOR']}.rb"))
    @directories = []

    puts "SLUG #{@slug}"
  end

  def valid?
    validate
    msgs.empty?
  end

  def setup
    fold 'Setting up build cache' do
      install
      fetch
      directories.each { |dir| add(dir) }
    end
  end

  def install
    `mkdir -p $DD_CASHER_DIR/bin/`
    `curl #{casher_url} #{debug_flags} -L -o #{BIN_PATH} -s --fail`
    `[ $? -ne 0 ] && echo 'Failed to fetch casher from GitHub, disabling cache.' && echo > #{BIN_PATH}`

    `chmod +x #{BIN_PATH}`
  end

  def add(path)
    run('add', path) if path
  end

  def fetch
    urls = [Shellwords.escape(fetch_url.to_s)]
    run('fetch', urls)
  end

  def push
    run('push', Shellwords.escape(push_url.to_s), assert: false)
  end

  def fetch_url(branch = 'master')
    url('GET', prefixed(branch), expires: fetch_timeout)
  end

  def push_url(branch = 'master')
    url('PUT', prefixed(branch), expires: push_timeout)
  end

  def fold(message = nil)
    @fold_count ||= 0
    @fold_count += 1

    puts `echo #{message}` if message
    yield
  end

  private

  def validate
    VALIDATE.each { |key, msg| msgs << msg unless s3_options[key] }
    system 'echo ' + MSGS[:config_missing] % msgs.join(', '), ansi: :red unless msgs.empty?
  end

  def run(command, args, _options = {})
    puts `rvm #{USE_RUBY} --fuzzy do #{BIN_PATH} #{command} #{Array(args).join(' ')}`
  end

  def fetch_timeout
    options[:fetch_timeout] || 60
  end

  def push_timeout
    options[:push_timeout] || 600
  end

  def location(path)
    Location.new(
      s3_options.fetch(:scheme, 'https'),
      s3_options.fetch(:region, 'us-east-1'),
      s3_options.fetch(:bucket),
      path
    )
  end

  def prefixed(branch)
    args = [branch, slug].compact
    args.map! { |arg| arg.to_s.gsub(/[^\w\.\_\-]+/, '') }
    '/' << args.join('/') << '.tbz'
  end

  def url(verb, path, options = {})
    AWS4Signature.new(key_pair, verb, location(path), options[:expires], start).to_uri.to_s.untaint
  end

  def key_pair
    KeyPair.new(s3_options[:access_key_id], s3_options[:secret_access_key])
  end

  def s3_options
    options[:s3] || {}
  end

  def options
    data || {}
  end

  def casher_url
    CASHER_URL % casher_branch
  end

  def casher_branch
    'production'
  end

  def debug_flags
    "-v -w '#{CURL_FORMAT}'" if data[:debug]
  end
end
