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
# https://github.com/travis-ci/travis-build/blob/d1c3be0b6aec5989872f9c534185585108125d0d/lib/travis/build/script/shared/directory_cache/s3/aws4_signature.rb

require 'uri'
require 'addressable/uri'
require 'digest/sha1'
require 'openssl'

class Cache
  class AWS4Signature
    def initialize(key_pair, verb, location, expires, timestamp = Time.now)
      @key_pair = key_pair
      @verb = verb
      @location = location
      @expires = expires
      @timestamp = timestamp
    end

    def to_uri
      query = canonical_query_params.dup
      query['X-Amz-Signature'] = OpenSSL::HMAC.hexdigest('sha256', signing_key, string_to_sign)

      Addressable::URI.new(
        scheme: @location.scheme,
        host: @location.hostname,
        path: @location.path,
        query_values: query
      )
    end

    private

    def date
      @timestamp.utc.strftime('%Y%m%d')
    end

    def timestamp
      @timestamp.utc.strftime('%Y%m%dT%H%M%SZ')
    end

    def query_string
      canonical_query_params.map do |key, value|
        "#{URI.encode(key.to_s, /[^~a-zA-Z0-9_.-]/)}=#{URI.encode(value.to_s, /[^~a-zA-Z0-9_.-]/)}"
      end.join('&')
    end

    def request_sha
      OpenSSL::Digest::SHA256.hexdigest(
        [
          @verb,
          @location.path,
          query_string,
          "host:#{@location.hostname}\n",
          'host',
          'UNSIGNED-PAYLOAD'
        ].join("\n")
      )
    end

    def canonical_query_params
      @canonical_query_params ||= {
        'X-Amz-Algorithm' => 'AWS4-HMAC-SHA256',
        'X-Amz-Credential' => "#{@key_pair.id}/#{date}/#{@location.region}/s3/aws4_request",
        'X-Amz-Date' => timestamp,
        'X-Amz-Expires' => @expires,
        'X-Amz-SignedHeaders' => 'host'
      }
    end

    def string_to_sign
      [
        'AWS4-HMAC-SHA256',
        timestamp,
        "#{date}/#{@location.region}/s3/aws4_request",
        request_sha
      ].join("\n")
    end

    def signing_key
      @signing_key ||= recursive_hmac(
        "AWS4#{@key_pair.secret}",
        date,
        @location.region,
        's3',
        'aws4_request'
      )
    end

    def recursive_hmac(*args)
      args.reduce { |k, d| OpenSSL::HMAC.digest('sha256', k, d) }
    end
  end
end
