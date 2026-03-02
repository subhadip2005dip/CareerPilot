import { NextRequest, NextResponse } from 'next/server';

const PYTHON_API_URL = process.env.PYTHON_API_URL;

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const sessionId = searchParams.get('sessionId');
    const category = searchParams.get('category');

    if (!PYTHON_API_URL) {
      return NextResponse.json(
        { error: 'Python API URL not configured' },
        { status: 500 }
      );
    }

    const response = await fetch(`${PYTHON_API_URL}/questions`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Interview API error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Interview questions error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch interview questions' },
      { status: 500 }
    );
  }
}
